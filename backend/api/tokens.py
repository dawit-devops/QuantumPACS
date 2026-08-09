import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt as _jwt

from api.jwt_compat import encode as jwt_encode
from api.jwt_keys import get_kid, get_private_key, get_public_key_pem
from config import config
from log import get_logger

log = get_logger(__name__)

_blocklist_redis = None
_last_blocklist_warn = 0.0
_BLOCKLIST_WARN_INTERVAL = 60.0


def _warn_blocklist_unavailable(reason):
    """Fail-open companion (R2-07): the token blocklist degrades to a no-op
    when Redis is down, so auth never 503s — but the degradation must be
    loud. Throttled: every auth request would otherwise log once per
    unavailability window on a busy server."""
    global _last_blocklist_warn
    now = time.monotonic()
    if now - _last_blocklist_warn >= _BLOCKLIST_WARN_INTERVAL:
        _last_blocklist_warn = now
        log.error(
            'Token blocklist unavailable — fail-open active (%s). '
            'Logout/revocation will not take effect until Redis recovers.',
            reason,
        )


def reset_blocklist_warn():
    """Test helper: clear the throttle so tests can assert the error log."""
    global _last_blocklist_warn
    _last_blocklist_warn = 0.0


async def _get_blocklist_redis():
    global _blocklist_redis
    if _blocklist_redis is None:
        try:
            from api.redis_client import get_client
            _blocklist_redis = await get_client(db=1)
        except Exception as e:
            _warn_blocklist_unavailable(f'init failed: {(str(e) or type(e).__name__)[:200]}')
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

    # R2-11: tokens are signed with RS256 (kid published via /api/oauth/jwks)
    # instead of the shared HS256 secret.
    return jwt_encode(
        payload,
        get_private_key(),
        algorithm='RS256',
        headers={'kid': get_kid()},
    )


async def block_token(token):
    try:
        data = _decode_any(token, {'verify_exp': False})
        jti = data.get('jti')
        if not jti:
            return
        r = await _get_blocklist_redis()
        if r is None:
            _warn_blocklist_unavailable('no redis client')
            return
        exp = data.get('exp')
        ttl = max(60, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 86400
        await r.set(f'blocklist:{jti}', '1', ex=ttl)
    except Exception as e:
        _warn_blocklist_unavailable(f'block failed: {(str(e) or type(e).__name__)[:200]}')


async def is_blocked(jti):
    try:
        r = await _get_blocklist_redis()
        if r is None:
            _warn_blocklist_unavailable('no redis client')
            return False
        return await r.exists(f'blocklist:{jti}') == 1
    except Exception as e:
        _warn_blocklist_unavailable(f'check failed: {(str(e) or type(e).__name__)[:200]}')
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
    # Carried so a refresh can prove the session predates any token_version
    # bump (password change, role change, deactivation) and reject it.
    if token_version is not None:
        refresh_payload['token_version'] = token_version
    exp = datetime.now(timezone.utc) + timedelta(days=14)
    refresh_payload['exp'] = exp
    refresh = jwt_encode(
        refresh_payload, get_private_key(), algorithm='RS256',
        headers={'kid': get_kid()},
    )
    return access, refresh


def _decode_any(token, options):
    """Verify a token signed with either the current RS256 key or the legacy
    HS256 secret. HS256 stays accepted for the rotation window so tokens
    minted before R2-11 keep working until they expire."""
    try:
        return _jwt.decode(
            token, get_public_key_pem(), algorithms=['RS256'], **options,
        )
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        return _jwt.decode(
            token, config['secret'], algorithms=['HS256'], **options,
        )


def verify_refresh_token(token):
    try:
        data = _decode_any(token, {'require': ['exp'], 'verify_exp': True})
        if data.get('type') != 'refresh':
            raise _jwt.InvalidTokenError('Not a refresh token')
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise


def verify_token(token):
    try:
        data = _decode_any(token, {'require': ['exp'], 'verify_exp': True})
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise
