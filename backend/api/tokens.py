from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt as _jwt

from api.jwt_compat import encode as jwt_encode, decode as jwt_decode
from config import config
from log import get_logger

log = get_logger(__name__)

_blocklist_redis = None


async def _get_blocklist_redis():
    global _blocklist_redis
    if _blocklist_redis is None:
        try:
            from api.redis_client import get_client
            _blocklist_redis = await get_client(db=1)
        except Exception:
            pass
    return _blocklist_redis


def create_token(user, expire=None, role=None, permissions=None, token_version=None):
    payload = {
        'jti': str(uuid4()),
        'id': user['id'],
        'admin': user['admin'],
    }
    if role is not None:
        payload['role'] = role
    if permissions is not None:
        payload['permissions'] = permissions
    if user.get('tenant'):
        payload['tenant'] = user['tenant']
    if token_version is not None:
        payload['token_version'] = token_version
    if not expire:
        expire = {'days': 14}

    exp = datetime.now(timezone.utc) + timedelta(**expire)
    payload['exp'] = exp

    return jwt_encode(
        payload,
        config['secret'],
        algorithm='HS256',
    )


async def block_token(token):
    try:
        data = jwt_decode(token, config['secret'], options={'verify_exp': False})
        jti = data.get('jti')
        if not jti:
            return
        r = await _get_blocklist_redis()
        if r is None:
            return
        exp = data.get('exp')
        ttl = max(60, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 86400
        await r.set(f'blocklist:{jti}', '1', ex=ttl)
    except Exception as e:
        log.warning('Failed to block token: %s', e)


async def is_blocked(jti):
    try:
        r = await _get_blocklist_redis()
        if r is None:
            return False
        return await r.exists(f'blocklist:{jti}') == 1
    except Exception:
        return False


def create_token_pair(user, role=None, permissions=None, token_version=None):
    access = create_token(user, expire={'hours': 1}, role=role, permissions=permissions, token_version=token_version)
    refresh_payload = {
        'jti': str(uuid4()),
        'id': user['id'],
        'type': 'refresh',
        'admin': user['admin'],
    }
    if user.get('tenant'):
        refresh_payload['tenant'] = user['tenant']
    exp = datetime.now(timezone.utc) + timedelta(days=14)
    refresh_payload['exp'] = exp
    refresh = jwt_encode(refresh_payload, config['secret'], algorithm='HS256')
    return access, refresh


def verify_refresh_token(token):
    try:
        data = jwt_decode(token, config['secret'], options={'require': ['exp'], 'verify_exp': True})
        if data.get('type') != 'refresh':
            raise _jwt.InvalidTokenError('Not a refresh token')
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise


def verify_token(token):
    try:
        data = jwt_decode(token, config['secret'], options={'require': ['exp'], 'verify_exp': True})
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise
