"""OAuth 2.0 / OpenID Connect authentication endpoints supporting multi-provider login,
PKCE authorization code flow, ID token verification via JWKS, and JIT user provisioning
with configurable default roles and tenant scoping."""
import hashlib
import json
import secrets
import base64
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient
from starlette.responses import RedirectResponse, JSONResponse

from api.response import ok, api_error, unauthorized
from api.tokens import (
    create_token_pair,
    verify_refresh_token, block_token, is_blocked,
)
from api.validate import read_body, _BodyTooLargeException
from config import config
from db.audit_log import AuditLog
from db.conn import get_conn
from db.oauth_providers import OAuthProviders
from db.users import Users
from log import get_logger, request_id_var

log = get_logger(__name__)

_JWKS_CLIENTS: dict = {}
_OAUTH_LOCK = None


async def _get_redis():
    from api.redis_client import get_client as get_redis
    return await get_redis()


def _base_url(request):
    return f"{request.url.scheme}://{request.url.hostname}:{request.url.port}"


async def _get_provider(idp_slug: str):
    async with get_conn() as conn:
        return await OAuthProviders(conn).get_by_slug(idp_slug)


async def _get_provider_by_id(provider_id: str):
    async with get_conn() as conn:
        return await OAuthProviders(conn).get_decrypted(provider_id)


def _get_jwks_client(jwks_uri):
    if jwks_uri not in _JWKS_CLIENTS:
        _JWKS_CLIENTS[jwks_uri] = PyJWKClient(jwks_uri, cache_keys=True)
    return _JWKS_CLIENTS[jwks_uri]


def _code_verifier():
    return secrets.token_urlsafe(64)


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


async def _store_state(state, verifier, provider_id=None, nonce=None):
    try:
        redis = await _get_redis()
        data = json.dumps({'verifier': verifier, 'provider_id': provider_id, 'nonce': nonce})
        await redis.set(f'oauth_state:{state}', data, ex=300)
    except Exception:
        log.warning('Failed to store OAuth state in Redis')


async def _verify_state(state):
    try:
        redis = await _get_redis()
        raw = await redis.get(f'oauth_state:{state}')
        if raw:
            await redis.delete(f'oauth_state:{state}')
            data = json.loads(raw if isinstance(raw, str) else raw.decode())
            return data.get('verifier'), data.get('provider_id'), data.get('nonce')
    except Exception:
        log.warning('Failed to verify OAuth state from Redis')
    return None, None, None


async def _exchange_code(code, verifier, provider):
    token_url = provider.get('token_url') or f"{provider['issuer'].rstrip('/')}/token"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': provider.get('redirect_uri', config.get('oauth_redirect_uri', '')),
        'client_id': provider['client_id'],
        'client_secret': provider.get('client_secret', ''),
    }
    if verifier:
        data['code_verifier'] = verifier

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            log.error('Token exchange failed: %s %s', resp.status_code, resp.text)
            return None
        return resp.json()


def _verify_id_token(id_token, provider):
    jwks_uri = provider.get('jwks_uri')
    if not jwks_uri:
        log.error('JWKS URI not configured for provider %s', provider.get('slug', provider['issuer']))
        return None
    try:
        client = _get_jwks_client(jwks_uri)
        signing_key = client.get_signing_key_from_jwt(id_token)
        audience = provider.get('client_id', config.get('oauth_client_id', ''))
        issuer = provider.get('issuer', config.get('oauth_issuer', ''))
        payload = jwt.decode(
            id_token, signing_key.key, algorithms=['RS256'],
            audience=audience, issuer=issuer,
            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub']},
        )
        return payload
    except jwt.ExpiredSignatureError:
        log.warning('id_token expired')
    except jwt.InvalidAudienceError:
        log.warning('id_token invalid audience')
    except jwt.InvalidIssuerError:
        log.warning('id_token invalid issuer')
    except Exception as e:
        log.warning('id_token verification failed: %s', e)
    return None


def _provider_groups_map(provider):
    """groups_map is stored as JSONB (asyncpg returns text) — normalize to a
    dict so the callback can consult it regardless of transport."""
    value = provider.get('groups_map')
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _role_from_groups(provider, claims):
    """R2-M7: first IdP group present in the claim that the provider maps to
    a role wins. No groups_claim configured, no groups in the claims, or an
    empty mapping → None (caller falls back to default_role)."""
    claim_name = provider.get('groups_claim')
    mapping = _provider_groups_map(provider)
    if not claim_name or not mapping or claims is None:
        return None
    groups = claims.get(claim_name) if hasattr(claims, 'get') else None
    if not groups:
        return None
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.split(',') if g.strip()]
    for group in groups:
        if group in mapping:
            return mapping[group]
    return None


async def _find_or_create_user(oauth_sub, email, name, provider, claims=None):
    async with get_conn() as conn:
        users = Users(conn)
        # `.table` is an instance attribute (pypika Table_); the class-level
        # `Users.table` access previously 500'd every SSO login.
        q = users.select('*').where(users.table.oauth_sub == oauth_sub)
        user = await conn.fetchrow(str(q))
        if user:
            user = dict(user)
            # R2-M7: on login, an IdP group mapping overrides the stored
            # role — group membership is the auditable grant surface and must
            # not drift from what the IdP currently says.
            mapped_slug = _role_from_groups(provider, claims)
            if mapped_slug:
                mapped_id = await conn.fetchval(
                    "SELECT id FROM roles WHERE slug = $1", mapped_slug
                )
                if mapped_id and user.get('role_id') != mapped_id:
                    await conn.execute(
                        "UPDATE users SET role_id = $1 WHERE id = $2",
                        mapped_id, user['id'],
                    )
                    await AuditLog(conn).log_event(
                        event_type='user.role_synced',
                        actor_id=user['id'],
                        resource_type='user',
                        resource_id=user['id'],
                        details={'role_slug': mapped_slug, 'source': 'oauth_groups'},
                        request_id=request_id_var.get(),
                    )
                    user['role_id'] = mapped_id
            return user

        # auto_provision=False providers map a closed user base: identities
        # must exist before login, JIT self-registration is refused.
        if provider.get('auto_provision') is False:
            return None

        # Least-privilege JIT (R2-H3): self-registering identities get the
        # 'patient' portal role unless the provider explicitly overrides it —
        # never a billing or clinical role by default. R2-M7: a configured
        # IdP group mapping takes precedence over default_role.
        role_slug = _role_from_groups(provider, claims) or provider.get('default_role') or config.get('oauth_default_role', 'patient')
        role_id = None
        if role_slug:
            role_id = await conn.fetchval(
                "SELECT id FROM roles WHERE slug = $1", role_slug
            )
        import binascii
        import hashlib as _hashlib
        import os
        placeholder = binascii.hexlify(_hashlib.sha256(os.urandom(32)).digest()).decode()
        username = email.split('@')[0] if email else f'oauth_{oauth_sub[:8]}'

        # R2-LOW: tenant-scoped providers bind provisioned users to the
        # provider's tenant (users.tenant holds the tenant slug).
        tenant = provider.get('tenant_id') or None
        if tenant:
            q2 = users.insert().columns(
                'username', 'password', 'admin', 'role_id', 'oauth_sub', 'email',
                'tenant',
            ).insert(username, placeholder, False, role_id, oauth_sub, email, tenant).returning('id')
        else:
            q2 = users.insert().columns(
                'username', 'password', 'admin', 'role_id', 'oauth_sub', 'email',
            ).insert(username, placeholder, False, role_id, oauth_sub, email).returning('id')
        new_id = await conn.fetchval(str(q2))

        await AuditLog(conn).log_event(
            event_type='user.provisioned',
            actor_id=new_id,
            resource_type='user',
            resource_id=new_id,
            details={'oauth_sub': oauth_sub, 'provider': provider.get('slug', ''),
                     'role_slug': role_slug, 'tenant': tenant},
            request_id=request_id_var.get(),
        )

        user = {'id': new_id, 'username': username, 'admin': False,
                'role_id': role_id, 'oauth_sub': oauth_sub, 'email': email,
                'tenant': tenant, 'token_version': 0}
        return user


async def oidc_discovery(request):
    base = _base_url(request)
    # R2-M5: advertise the same issuer that mints tokens — config key
    # `token_issuer` is the single source of truth; the request-derived base
    # URL remains the fallback when it is unset.
    return JSONResponse({
        'issuer': config.get('token_issuer') or f'{base}/api',
        'authorization_endpoint': f'{base}/api/oauth/login',
        'token_endpoint': f'{base}/api/oauth/token',
        'jwks_uri': f'{base}/api/oauth/jwks',
        'response_types_supported': ['code'],
        'response_modes_supported': ['query', 'form_post'],
        'grant_types_supported': ['authorization_code', 'refresh_token'],
        'subject_types_supported': ['public'],
        # Only RS256: the JWKS endpoint publishes the RSA key; the legacy
        # HS256 secret signs nothing that this endpoint advertises.
        'id_token_signing_alg_values_supported': ['RS256'],
        'scopes_supported': ['openid', 'email', 'profile'],
        'token_endpoint_auth_methods_supported': ['client_secret_basic', 'client_secret_post'],
        'claims_supported': ['sub', 'iss', 'aud', 'exp', 'iat', 'jti', 'typ',
                             'email', 'name', 'role', 'permissions',
                             'tenant', 'token_version'],
        'code_challenge_methods_supported': ['S256'],
    })


def oidc_jwks(request):
    # R2-11: discovery advertises this jwks_uri; publish the RSA public key
    # that signs our access/refresh tokens (see api.jwt_keys).
    from api.jwt_keys import get_jwk
    return JSONResponse({'keys': [get_jwk()]})


async def oauth_login(request):
    # IAM audit M-1: the OAuth entry points were the only authn surfaces
    # without a throttle. Same bucket as password login — per-IP window with
    # lockout — so federated flows cannot be hammered either.
    from api.ratelimit import login_bucket
    ip = request.client.host if request.client else 'unknown'
    allowed, msg = await login_bucket.check(ip)
    if not allowed:
        return api_error('RATE_LIMITED', msg, status=429)

    idp_slug = request.query_params.get('idp', '')
    if idp_slug:
        provider = await _get_provider(idp_slug)
        if not provider:
            return api_error('PROVIDER_NOT_FOUND', f'OAuth provider not found: {idp_slug}', status=404)
        if not provider.get('enabled'):
            return api_error('PROVIDER_DISABLED', 'OAuth provider is disabled', status=403)
    else:
        issuer = config.get('oauth_issuer', '')
        client_id = config.get('oauth_client_id', '')
        if not issuer or not client_id:
            return api_error('OAUTH_NOT_CONFIGURED', 'OAuth is not configured', status=501)
        provider = {
            'issuer': issuer,
            'client_id': client_id,
            'client_secret': config.get('oauth_client_secret', ''),
            'redirect_uri': config.get('oauth_redirect_uri', ''),
            'token_url': config.get('oauth_token_url', ''),
            'jwks_uri': config.get('oauth_jwks_uri', ''),
            'scope': config.get('oauth_scope', 'openid email profile'),
        }

    verifier = _code_verifier()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    provider_id = provider.get('id') if idp_slug else None
    await _store_state(state, verifier, provider_id, nonce)

    auth_url = f"{provider['issuer'].rstrip('/')}/authorize"
    params = {
        'response_type': 'code',
        'client_id': provider['client_id'],
        'redirect_uri': provider.get('redirect_uri', config.get('oauth_redirect_uri', '')),
        'scope': provider.get('scope', 'openid email profile'),
        'state': state,
        'nonce': nonce,
        'code_challenge': _code_challenge(verifier),
        'code_challenge_method': 'S256',
    }
    redirect = f"{auth_url}?{urlencode(params)}"
    log.info('OAuth login redirect to %s (provider=%s)', auth_url, provider.get('slug', 'default'))
    return RedirectResponse(url=redirect, status_code=302)


async def oauth_callback(request):
    # IAM audit M-1: the code-exchange endpoint consumes the most expensive
    # resources (Redis state, IdP round-trip) — throttle it and record
    # failures so stuffing attempts land in the bucket and the audit trail.
    from api.ratelimit import login_bucket
    ip = request.client.host if request.client else 'unknown'
    allowed, msg = await login_bucket.check(ip)
    if not allowed:
        return api_error('RATE_LIMITED', msg, status=429)

    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')

    if error:
        await login_bucket.record(ip, success=False)
        return unauthorized(f'OAuth provider returned error: {error}')
    if not code or not state:
        await login_bucket.record(ip, success=False)
        return api_error('MISSING_PARAMS', 'Missing code or state parameter', status=400)

    verifier, provider_id, nonce = await _verify_state(state)
    if verifier is None:
        await login_bucket.record(ip, success=False)
        return api_error('INVALID_STATE', 'State mismatch or expired', status=401)

    if provider_id:
        provider = await _get_provider_by_id(provider_id)
        if not provider:
            return api_error('PROVIDER_NOT_FOUND', 'OAuth provider not found', status=404)
        if not provider.get('enabled'):
            return api_error('PROVIDER_DISABLED', 'OAuth provider is disabled', status=403)
    else:
        provider = {
            'issuer': config.get('oauth_issuer', ''),
            'client_id': config.get('oauth_client_id', ''),
            'client_secret': config.get('oauth_client_secret', ''),
            'redirect_uri': config.get('oauth_redirect_uri', ''),
            'token_url': config.get('oauth_token_url', ''),
            'jwks_uri': config.get('oauth_jwks_uri', ''),
        }

    tokens = await _exchange_code(code, verifier, provider)
    if tokens is None:
        return api_error('TOKEN_EXCHANGE_FAILED', 'Failed to exchange authorization code', status=502)

    id_token = tokens.get('id_token')
    if not id_token:
        return api_error('MISSING_ID_TOKEN', 'IdP did not return an id_token', status=502)

    claims = _verify_id_token(id_token, provider)
    if claims is None:
        return api_error('INVALID_ID_TOKEN', 'id_token verification failed', status=401)

    oauth_sub = claims.get('sub')
    email = claims.get('email') or claims.get('preferred_username', '')
    name = claims.get('name', '')
    if nonce:
        # Replay protection (R2-M4): when the IdP cooperates the id_token
        # must echo the nonce we sent; providers that omit nonce entirely are
        # tolerated (PKCE + single-use state still bind the code).
        if claims.get('nonce') != nonce:
            return api_error('NONCE_MISMATCH', 'Login nonce mismatch', status=401)
    elif claims.get('nonce') is not None:
        return api_error('NONCE_MISMATCH', 'Unexpected nonce claim', status=401)
    user = await _find_or_create_user(oauth_sub, email, name, provider, claims)
    if user is None:
        # auto_provision=False: the identity has no account and the provider
        # forbids JIT self-registration. 403 keeps the 404-vs-403 semantics:
        # an unprovisioned identity is an authorization decision, not a leak.
        return api_error(
            'ACCOUNT_NOT_PROVISIONED',
            'Account not provisioned — contact your administrator',
            status=403,
        )

    # Role/permissions always come from the DB row (the provider default_role
    # applies only at provisioning); minting from provider config would let a
    # stale default leak grants to a demoted user and would produce a token
    # with no permissions claim at all for existing users.
    try:
        async with get_conn() as conn:
            user_row = await Users(conn).get_user_row(user['id'])
            if user_row and user_row.get('status') == 'active':
                role_slug, permissions = await Users(conn).get_user_role(user['id'])
    except RuntimeError:
        user_row = None
        role_slug, permissions = None, []

    if not user_row or user_row.get('status') != 'active':
        await login_bucket.record(ip, success=False)
        return unauthorized('Account unavailable')

    # The SSO JWT must carry the same tenant claim as the password-login
    # path (users.py) — without it the tenancy gate sees an unscoped identity
    # and tenant isolation is bypassed for SSO sessions.
    token_user = {'id': user['id'], 'admin': bool(user_row.get('admin', False))}
    if user_row.get('tenant'):
        token_user['tenant'] = user_row['tenant']
    token = create_token_pair(
        token_user,
        role=role_slug,
        permissions=permissions,
        token_version=user_row.get('token_version', 0),
    )
    access, refresh = token
    await login_bucket.record(ip, success=True)

    # R2-LOW: the refresh token rides ONLY as an HttpOnly cookie — never in a
    # JSON body where XSS or a compromised extension could read it.
    resp = ok({
        'token': access,
        'access_token': access,
        'user': {
            'id': user['id'],
            'username': user.get('username', email),
            'email': email,
        },
    })
    resp.set_cookie(key='token', value=access, httponly=True, samesite='strict', secure=True, path='/')
    # Same cookie contract as the password login: the refresh token rides
    # only as an HttpOnly cookie scoped to /api/auth so the shared refresh
    # endpoint can rotate it. 1-hour access tokens + rotation, not a 14-day
    # bearer (R2-H5).
    resp.set_cookie(
        key='refresh_token', value=refresh, httponly=True,
        samesite='strict', secure=True, path='/api/auth',
    )
    return resp


async def oauth_token_exchange(request):
    ip = request.client.host if request.client else 'unknown'
    from api.ratelimit import refresh_bucket
    allowed, msg = await refresh_bucket.check(ip)
    if not allowed:
        return api_error('RATE_LIMITED', msg, status=429)
    # R2-M6: capped read — oversized bodies → 413, malformed JSON → 400
    # (a raw request.json() here turned malformed bodies into a 500).
    try:
        raw = await read_body(request)
    except _BodyTooLargeException:
        return api_error('BODY_TOO_LARGE', 'Request body exceeds 1MB limit', status=413)
    if raw:
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return api_error('INVALID_JSON', 'Malformed JSON body', status=400)
    else:
        body = {}
    if not isinstance(body, dict):
        return api_error('INVALID_JSON', 'Malformed JSON body', status=400)
    grant_type = body.get('grant_type', 'authorization_code')
    code = body.get('code', '')
    refresh_token = body.get('refresh_token', '')

    if grant_type == 'authorization_code' and code:
        verifier, provider_id, _nonce = await _verify_state(request.query_params.get('state', ''))
        return api_error('INVALID_STATE', 'Use the callback endpoint for authorization_code flow', status=400)

    if grant_type == 'refresh_token' and refresh_token:
        # Only a real refresh token (type claim, verified signature) may be
        # exchanged. Access tokens are rejected here; the presented token is
        # blocked (rotation) and user status + token_version are re-read from
        # the DB so deactivated/demoted users cannot keep minting credentials.
        try:
            payload = verify_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return api_error('TOKEN_EXPIRED', 'Refresh token expired', status=401)
        except jwt.InvalidTokenError:
            return unauthorized('Invalid or expired refresh token')

        # R2-H4: refresh grants fail CLOSED when the blocklist cannot be
        # checked — a revoked session must not mint fresh credentials just
        # because Redis is down.
        if await is_blocked(payload.get('jti', ''), fail_closed=True):
            return unauthorized('Refresh token revoked')

        await block_token(refresh_token)

        try:
            async with get_conn() as conn:
                user_row = await Users(conn).get_user_row(payload['id'])
                if user_row and user_row.get('status') == 'active':
                    role_slug, permissions = await Users(conn).get_user_role(payload['id'])
        except RuntimeError:
            user_row = None
            role_slug, permissions = None, []
        if not user_row or user_row.get('status') != 'active':
            return unauthorized('Account unavailable')
        if (user_row.get('token_version') or 0) != payload.get('token_version', 0):
            return unauthorized('Session invalidated')

        user_data = {'id': payload['id'], 'admin': bool(user_row.get('admin', False))}
        if user_row.get('tenant'):
            user_data['tenant'] = user_row['tenant']
        token_version = user_row.get('token_version') or 0
        access, new_refresh = create_token_pair(
            user_data, role=role_slug, permissions=permissions,
            token_version=token_version,
        )
        await refresh_bucket.record(ip, success=True)
        resp = ok({
            'access_token': access,
            'token_type': 'Bearer',
            'expires_in': 3600,
        })
        # R2-LOW: cookie-only refresh delivery. Path=/api so BOTH the shared
        # refresh endpoint (/api/auth/refresh) and this RFC 6749 token
        # endpoint can read the rotating credential.
        resp.set_cookie(
            key='refresh_token', value=new_refresh, httponly=True,
            samesite='strict', secure=True, path='/api',
        )
        return resp

    return api_error('UNSUPPORTED_GRANT', 'Unsupported grant_type', status=400)
