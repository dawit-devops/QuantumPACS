"""Starlette authentication backend — JWT token verification on every API request.
Supports bearer tokens via X-Auth-Pacs header, query parameter tokens for WebSocket,
and shared-file access tokens for expiring share links."""
import time
from collections import OrderedDict

import jwt as _jwt

from api.response import unauthorized
from api.tokens import verify_token, is_blocked
from api.ratelimit import RedisTokenBucket
from config import config  # noqa: F401  (module attribute patched by tests)
from db.conn import get_conn
from db.share_files import SharedFiles
from db.users import Users
from log import get_logger
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, BaseUser,
    AuthCredentials
)

log = get_logger(__name__)

_app = None
_MAX_CACHE_SIZE = 5000


def set_app(app):
    global _app
    _app = app


def _get_state():
    if _app is None:
        return None
    if not hasattr(_app.state, 'auth_state'):
        _app.state.auth_state = AuthState()
    return _app.state.auth_state


class AuthState:
    def __init__(self):
        self.active_cache: OrderedDict = OrderedDict()
        self.cache_redis = None
        self.api_key_limiter = RedisTokenBucket(max_attempts=100, window_seconds=60)


async def _get_cache_redis():
    state = _get_state()
    if state is None:
        return None
    if state.cache_redis is None:
        try:
            from api.redis_client import get_client
            state.cache_redis = await get_client(db=2)
        except Exception:
            pass
    return state.cache_redis


async def _get_cached_active(user_id):
    state = _get_state()
    r = await _get_cache_redis()
    if r is not None:
        try:
            val = await r.get(f'auth:active:{user_id}')
            if val is not None:
                return val == b'1'
        except Exception:
            pass
    if state is not None:
        entry = state.active_cache.get(user_id)
        if entry and time.monotonic() < entry[1]:
            return entry[0]
    return None


async def _set_cached_active(user_id, active, ttl=60):
    state = _get_state()
    r = await _get_cache_redis()
    if r is not None:
        try:
            await r.set(f'auth:active:{user_id}', b'1' if active else b'0', ex=ttl)
        except Exception:
            pass
    if state is not None:
        state.active_cache[user_id] = (active, time.monotonic() + ttl)
        state.active_cache.move_to_end(user_id)
        while len(state.active_cache) > _MAX_CACHE_SIZE:
            state.active_cache.popitem(last=False)


async def _cleanup_cache():
    state = _get_state()
    if state is None:
        return
    now = time.monotonic()
    stale = [k for k, v in list(state.active_cache.items()) if now >= v[1]]
    for k in stale:
        del state.active_cache[k]


class User(BaseUser):
    def __init__(self, data):
        self.id = data['id']
        self.admin = data.get('admin', False)
        self.role_slug = data.get('role', '')
        self.permissions = data.get('permissions', [])
        self.tenant = data.get('tenant')

    @property
    def is_authenticated(self):
        return True

    @property
    def display_name(self):
        return str(self.id)

    def can_access_tenant(self, tenant_slug):
        if not tenant_slug:
            return True
        if self.admin:
            return True
        return self.tenant == tenant_slug

    def to_dict(self):
        d = {
            'id': self.id,
            'admin': self.admin,
            'role': self.role_slug,
            'permissions': self.permissions,
        }
        if self.tenant:
            d['tenant'] = self.tenant
        return d


class TokenAuth(AuthenticationBackend):
    _PUBLIC_PATHS = frozenset({
        '/api/login',
        '/api/v2/health',
        '/api/health',
        '/api/auth/refresh',
        '/api/auth/logout',
        '/api/oauth/login',
        '/api/oauth/callback',
        '/api/.well-known/openid-configuration',
        '/api/oauth/token',
        '/api/v2/oauth/login',
        '/api/v2/oauth/callback',
        '/api/v2/.well-known/openid-configuration',
        '/api/v2/oauth/token',
        '/api/v2/auth/refresh',
        '/api/v2/auth/logout',
        '/api/v2/login',
    })

    async def authenticate(self, request):
        path = request.url.path
        if not path.startswith('/api'):
            return
        if path in self._PUBLIC_PATHS:
            return
        if request.scope.get('method') == 'OPTIONS':
            return

        api_key = request.headers.get('X-API-Key')
        if api_key:
            state = _get_state()
            limiter = state.api_key_limiter if state else None
            if limiter is not None:
                ok, msg = await limiter.check(api_key)
                if not ok:
                    raise AuthenticationError('Rate limited')
                await limiter.record(api_key)
            from db.api_keys import ApiKeys
            try:
                async with get_conn() as conn:
                    record = await ApiKeys(conn).validate(api_key)
            except Exception:
                raise AuthenticationError('Invalid auth')
            if not record:
                raise AuthenticationError('Invalid auth')
            user = User({
                'id': f'svc_{record["service_name"]}',
                'admin': False,
                'role': '',
                'permissions': record.get('permissions', []),
            })
            return AuthCredentials(["authenticated"]), user

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

                if file_id and (path.startswith(f'/api/files/{file_id}') or path.startswith('/api/ws_token')):
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
                            active, token_version = await Users(conn).get_auth_state(data['id'])
                    except Exception as e:
                        log.error('is_active check failed: %s', e)
                        raise AuthenticationError('Auth backend error')
                    await _set_cached_active(data['id'], active)
                    if not active:
                        raise AuthenticationError('Deactivated user')
                    jwt_version = data.get('token_version', 0)
                    if jwt_version != token_version:
                        raise AuthenticationError('Token invalidated')
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
        return unauthorized(str(exc))
