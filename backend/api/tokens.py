import time
from collections import OrderedDict
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

# Claims minted on every token (R2-M5): iss/aud/iat/typ make each token
# self-describing so verifiers can enforce token-type separation instead of
# guessing from payload shape.
_TOKEN_ISSUER_FALLBACK = 'quantumpacs'
_ACCESS_AUDIENCE = 'quantumpacs:api'
_REFRESH_AUDIENCE = 'quantumpacs:refresh'

# R2-M5: minted iss and the OIDC discovery issuer (/api/oauth/.../openid-configuration)
# share a single source of truth — the `token_issuer` config key. Operators can
# pin it to the advertised base URL (e.g. https://pacs.example.com/api); the
# fallback keeps the legacy non-URL issuer for existing deployments.
def _token_issuer():
    return config.get('token_issuer') or _TOKEN_ISSUER_FALLBACK

# R2-H4: fail-closed companion to the blocklist. Refresh validation must not
# mint credentials while the revocation store is unreachable, so is_blocked()
# records the last moment it could PROVE anything about the blocklist and
# refresh checks treat an outage longer than _BLOCKLIST_OUTAGE_LIMIT as
# "invalidated": the client is forced back to a full login.
_last_redis_ok = time.monotonic()
_BLOCKLIST_OUTAGE_LIMIT = 60.0


def _mark_redis_ok():
    """Last moment a blocklist Redis interaction actually succeeded."""
    global _last_redis_ok
    _last_redis_ok = time.monotonic()


def _blocklist_outage_seconds():
    return time.monotonic() - _last_redis_ok


def reset_blocklist_health():
    """Test helper: drop cached client + last-good timestamp so tests can
    simulate cold start / outages deterministically."""
    global _blocklist_redis, _last_redis_ok
    _blocklist_redis = None
    _last_redis_ok = time.monotonic()

# Bounded in-process overlay of recently revoked tokens (R2-H4). Redis is the
# primary blocklist; when it is down the gate fails OPEN for old revocations,
# but a token revoked moments before the outage must still die. block_token
# records every revocation here (TTL-bounded by the token's own expiry), and
# is_blocked consults it first — so replayed or stolen tokens kill-switched
# just before a Redis outage cannot ride out the outage.
_local_denylist: 'OrderedDict[str, float]' = OrderedDict()
_LOCAL_DENYLIST_MAX = 200_000
_LOCAL_DENYLIST_SKEW = 3600


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


def reset_local_denylist():
    """Test helper: drop the in-process revocation overlay."""
    _local_denylist.clear()


def _local_block(jti, exp_ts):
    """Record jti in the bounded in-process overlay. TTL is capped by the
    token's own expiry plus skew; expired entries never survive a purge."""
    now = time.time()
    deadline = min(exp_ts or now + 7 * 86400, now + 14 * 86400 + _LOCAL_DENYLIST_SKEW)
    if deadline <= now:
        return
    try:
        _local_denylist[jti] = deadline
        _local_denylist.move_to_end(jti)
        if len(_local_denylist) > _LOCAL_DENYLIST_MAX:
            expired = [k for k, v in _local_denylist.items() if v <= now]
            for k in expired:
                del _local_denylist[k]
            while len(_local_denylist) > _LOCAL_DENYLIST_MAX:
                _local_denylist.popitem(last=False)
    except Exception:
        # The overlay must never break revocation or auth.
        pass


def _local_is_blocked(jti):
    try:
        deadline = _local_denylist.get(jti)
        if deadline is None:
            return False
        if deadline <= time.time():
            del _local_denylist[jti]
            return False
        return True
    except Exception:
        return False


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
    now = datetime.now(timezone.utc)
    payload = {
        'jti': str(uuid4()),
        'iat': int(now.timestamp()),
        'iss': _token_issuer(),
        'aud': _ACCESS_AUDIENCE,
        'typ': 'at+jwt',
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
        # P2-3: lifetime is a config key so the Settings page can surface a
        # stored override without editing code.
        expire = {'days': int(config.get('token_expiry_days', 14))}

    exp = now + timedelta(**expire)
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
        # Local overlay first: revocation must survive a Redis outage.
        _local_block(jti, data.get('exp'))
        r = await _get_blocklist_redis()
        if r is None:
            _warn_blocklist_unavailable('no redis client')
            return
        exp = data.get('exp')
        ttl = max(60, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 86400
        await r.set(f'blocklist:{jti}', '1', ex=ttl)
        _mark_redis_ok()
    except Exception as e:
        _warn_blocklist_unavailable(f'block failed: {(str(e) or type(e).__name__)[:200]}')


async def is_blocked(jti, *, fail_closed=False):
    """Blocklist probe.

    fail_closed=False (access-token verification): Redis down → False. JWT
    verification is stateless and must keep working through an outage; the
    in-process overlay (checked first) still catches just-revoked tokens.

    fail_closed=True (refresh-token validation): any inability to PROVE the
    token is unrevoked → True. A denied refresh is a safe error (client
    re-logins); a granted refresh during an outage could mint fresh
    credentials for a session revoked moments earlier. An outage longer than
    _BLOCKLIST_OUTAGE_LIMIT invalidates refresh validation outright — the
    first successful probe after recovery still denies, forcing re-login
    before refreshes resume.
    """
    if _local_is_blocked(jti):
        return True
    stale_outage = fail_closed and _blocklist_outage_seconds() > _BLOCKLIST_OUTAGE_LIMIT
    try:
        r = await _get_blocklist_redis()
        if r is None:
            _warn_blocklist_unavailable('no redis client')
            return True if fail_closed else False
        blocked = await r.exists(f'blocklist:{jti}') == 1
        _mark_redis_ok()
        if stale_outage:
            # Refresh tokens are invalidated: the token cannot be trusted
            # while the blocklist was unproven for the whole outage window.
            _warn_blocklist_unavailable(f'outage >{_BLOCKLIST_OUTAGE_LIMIT:.0f}s — refresh denied')
            return True
        return blocked
    except Exception as e:
        _warn_blocklist_unavailable(f'check failed: {(str(e) or type(e).__name__)[:200]}')
        return True if fail_closed else False


def create_token_pair(user, role=None, permissions=None, token_version=None):
    access = create_token(user, expire={'hours': 1}, role=role, permissions=permissions, token_version=token_version)
    now = datetime.now(timezone.utc)
    refresh_payload = {
        'jti': str(uuid4()),
        'iat': int(now.timestamp()),
        'iss': _token_issuer(),
        'aud': _REFRESH_AUDIENCE,
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
    exp = now + timedelta(days=14)
    refresh_payload['exp'] = exp
    refresh = jwt_encode(
        refresh_payload, get_private_key(), algorithm='RS256',
        headers={'kid': get_kid()},
    )
    return access, refresh


def _decode_any(token, options):
    """Verify a token signed with either the current RS256 key or the legacy
    HS256 secret. HS256 stays accepted for the rotation window so tokens
    minted before R2-11 keep working until they expire.
    Audience is validated by the callers (only when the claim exists), so
    decode never needs an audience argument."""
    opts = {
        'verify_exp': True,
        'require': ['exp'],
        'verify_aud': False,
    }
    opts.update(options or {})
    try:
        return _jwt.decode(
            token, get_public_key_pem(), algorithms=['RS256'], options=opts,
        )
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        return _jwt.decode(
            token, config['secret'], algorithms=['HS256'], options=opts,
        )


def verify_refresh_token(token):
    try:
        data = _decode_any(token, {'require': ['exp'], 'verify_exp': True, 'verify_aud': False})
        if data.get('type') != 'refresh':
            raise _jwt.InvalidTokenError('Not a refresh token')
        # Audience is enforced when the claim exists (new tokens); legacy
        # tokens without aud keep working through the rotation window.
        aud = data.get('aud')
        if aud is not None and aud != _REFRESH_AUDIENCE:
            raise _jwt.InvalidTokenError('Wrong audience')
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise


def verify_token(token):
    try:
        data = _decode_any(token, {'require': ['exp'], 'verify_exp': True, 'verify_aud': False})
        if data.get('type') == 'refresh':
            # AT-1: a refresh token outlives access tokens by 13 days and
            # must never authorize API requests. Type separation is enforced
            # at every verification site, not just the refresh endpoint.
            raise _jwt.InvalidTokenError('Refresh tokens cannot authorize API requests')
        aud = data.get('aud')
        if aud is not None and aud != _ACCESS_AUDIENCE:
            raise _jwt.InvalidTokenError('Wrong audience')
        return data
    except _jwt.ExpiredSignatureError:
        raise
    except _jwt.InvalidTokenError:
        raise
