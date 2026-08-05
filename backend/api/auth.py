"""Starlette authentication backend — JWT token verification on every API request.
Supports bearer tokens via X-Auth-Pacs header, query parameter tokens for WebSocket,
and shared-file access tokens for expiring share links."""
import time

import jwt as _jwt

from api.response import unauthorized
from api.tokens import verify_token, is_blocked
from config import config
from db.conn import get_conn
from db.share_files import SharedFiles
from db.users import Users
from log import get_logger
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, BaseUser,
    AuthCredentials
)

log = get_logger(__name__)

_active_cache = {}
_cache_redis = None


def _get_cache_redis():
    global _cache_redis
    if _cache_redis is None:
        try:
            import redis.asyncio as _aioredis
            host = config.get('redis_host', 'localhost')
            port = int(config.get('redis_port', '6379'))
            password = config.get('redis_password') or None
            _cache_redis = _aioredis.Redis(
                host=host, port=port, password=password, db=2,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        except Exception:
            pass
    return _cache_redis


async def _get_cached_active(user_id):
    r = _get_cache_redis()
    if r is not None:
        try:
            val = await r.get(f'auth:active:{user_id}')
            if val is not None:
                return val == b'1'
        except Exception:
            pass
    entry = _active_cache.get(user_id)
    if entry and time.monotonic() < entry[1]:
        return entry[0]
    return None


async def _set_cached_active(user_id, active, ttl=60):
    r = _get_cache_redis()
    if r is not None:
        try:
            await r.setex(f'auth:active:{user_id}', ttl, b'1' if active else b'0')
        except Exception:
            pass
    _active_cache[user_id] = (active, time.monotonic() + ttl)


class User(BaseUser):
    def __init__(self, data):
        self.id = data['id']
        self.admin = data.get('admin', False)

    @property
    def is_authenticated(self):
        return True

    @property
    def display_name(self):
        return str(self.id)

    def to_dict(self):
        return {
            'id': self.id,
            'admin': self.admin,
        }


class TokenAuth(AuthenticationBackend):
    async def authenticate(self, request):
        path = request.url.path
        if not path.startswith('/api'):
            return
        if path == '/api/login' or path == '/api/health':
            return
        if request.scope.get('method') == 'OPTIONS':
            return

        data = None
        if request.url.scheme != 'ws':
            auth = request.headers.get('X-Auth-Pacs')
            if not auth:
                bearer = request.headers.get('Authorization')
                if bearer and bearer.startswith('Bearer '):
                    auth = bearer[7:]
            if not auth:
                auth = request.query_params.get('token')
            if not auth:
                auth = request.cookies.get('token')
            if not auth:
                raise AuthenticationError('Invalid auth')

            credentials = auth
            try:
                data = verify_token(credentials)
            except _jwt.ExpiredSignatureError:
                raise AuthenticationError('Token expired')
            except _jwt.InvalidTokenError:
                try:
                    async with get_conn() as conn:
                        file_id = await SharedFiles(conn).check(credentials)
                except Exception as e:
                    log.error('Share-file check failed: %s', e)
                    raise AuthenticationError('Invalid auth')

                if file_id and (path.startswith(f'/api/files/{file_id}') or path.startswith(f'/api/ws_token')):
                    data = {'id': credentials, 'admin': False}
                else:
                    raise AuthenticationError('Invalid auth')
            else:
                if await is_blocked(data.get('jti', '')):
                    raise AuthenticationError('Token revoked')
                cached = await _get_cached_active(data['id'])
                if cached is False:
                    raise AuthenticationError('Deactivated user')
                if cached is None:
                    try:
                        async with get_conn() as conn:
                            active = await Users(conn).is_active(data['id'])
                    except Exception as e:
                        log.error('is_active check failed: %s', e)
                        raise AuthenticationError('Auth backend error')
                    await _set_cached_active(data['id'], active)
                    if not active:
                        raise AuthenticationError('Deactivated user')
        else:
            token = request.query_params.get('token')
            if not token:
                raise AuthenticationError('Invalid auth')
            try:
                data = verify_token(token)
            except _jwt.ExpiredSignatureError:
                raise AuthenticationError('Token expired')
            except _jwt.InvalidTokenError:
                raise AuthenticationError('Invalid auth')

            data = {'id': data['id'], 'admin': data['admin']}

        if not data:
            raise AuthenticationError('Invalid auth')

        return AuthCredentials(["authenticated"]), User(data)

    @staticmethod
    def on_auth_error(request, exc):
        resp = unauthorized(str(exc))
        cors_origin = config.get('cors_origins', '*')
        resp.headers['Access-Control-Allow-Origin'] = cors_origin
        resp.headers['Access-Control-Allow-Methods'] = 'OPTIONS,GET,POST,DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Origin,Accept,X-Auth-Pacs,Content-Type,X-Requested-With'
        return resp
