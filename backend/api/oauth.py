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
from api.tokens import create_token, create_token_pair, verify_token
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
        q = OAuthProviders(conn).select('*').where(
            OAuthProviders.table.slug == idp_slug
        )
        row = await conn.fetchrow(str(q))
        if row:
            return dict(row)
        q = OAuthProviders(conn).select('*').where(
            OAuthProviders.table.issuer == idp_slug
        )
        row = await conn.fetchrow(str(q))
        return dict(row) if row else None


async def _get_provider_by_id(provider_id: str):
    async with get_conn() as conn:
        return await OAuthProviders(conn).get(provider_id)


def _get_jwks_client(jwks_uri):
    if jwks_uri not in _JWKS_CLIENTS:
        _JWKS_CLIENTS[jwks_uri] = PyJWKClient(jwks_uri, cache_keys=True)
    return _JWKS_CLIENTS[jwks_uri]


def _code_verifier():
    return secrets.token_urlsafe(64)


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


async def _store_state(state, verifier, provider_id=None):
    try:
        redis = await _get_redis()
        data = json.dumps({'verifier': verifier, 'provider_id': provider_id})
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
            return data.get('verifier'), data.get('provider_id')
    except Exception:
        log.warning('Failed to verify OAuth state from Redis')
    return None, None


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


async def _find_or_create_user(oauth_sub, email, name, provider):
    groups = []
    async with get_conn() as conn:
        q = Users(conn).select('*').where(Users.table.oauth_sub == oauth_sub)
        user = await conn.fetchrow(str(q))
        if user:
            user = dict(user)
            if provider.get('groups_claim'):
                groups = user.get('groups') or []
            return user, groups

        role_slug = provider.get('default_role') or config.get('oauth_default_role', 'cashier')
        role_id = None
        if role_slug:
            role_id = await conn.fetchval(
                f"SELECT id FROM roles WHERE slug = '{role_slug}'"
            )
        import binascii, hashlib as _hashlib, os
        placeholder = binascii.hexlify(_hashlib.sha256(os.urandom(32)).digest()).decode()
        username = email.split('@')[0] if email else f'oauth_{oauth_sub[:8]}'

        q2 = Users(conn).insert().columns(
            'username', 'password', 'admin', 'role_id', 'oauth_sub', 'email',
        ).insert(username, placeholder, False, role_id, oauth_sub, email).returning('id')
        new_id = await conn.fetchval(str(q2))

        await AuditLog(conn).log_event(
            event_type='user.provisioned',
            actor_id=new_id,
            resource_type='user',
            resource_id=new_id,
            details={'oauth_sub': oauth_sub, 'provider': provider.get('slug', '')},
            request_id=request_id_var.get(),
        )

        user = {'id': new_id, 'username': username, 'admin': False,
                'role_id': role_id, 'oauth_sub': oauth_sub, 'email': email}
        return user, []


async def oidc_discovery(request):
    base = _base_url(request)
    return JSONResponse({
        'issuer': f'{base}/api',
        'authorization_endpoint': f'{base}/api/oauth/login',
        'token_endpoint': f'{base}/api/oauth/token',
        'jwks_uri': f'{base}/api/oauth/jwks',
        'response_types_supported': ['code'],
        'response_modes_supported': ['query', 'form_post'],
        'grant_types_supported': ['authorization_code', 'refresh_token'],
        'subject_types_supported': ['public'],
        'id_token_signing_alg_values_supported': ['HS256', 'RS256'],
        'scopes_supported': ['openid', 'email', 'profile'],
        'token_endpoint_auth_methods_supported': ['client_secret_basic', 'client_secret_post'],
        'claims_supported': ['sub', 'iss', 'aud', 'exp', 'iat', 'email', 'name'],
        'code_challenge_methods_supported': ['S256'],
    })


async def oauth_login(request):
    idp_slug = request.query_params.get('idp', '')
    if idp_slug:
        provider = await _get_provider(idp_slug)
        if not provider:
            return api_error('PROVIDER_NOT_FOUND', f'OAuth provider not found: {idp_slug}', status=404)
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
    provider_id = provider.get('id') if idp_slug else None
    await _store_state(state, verifier, provider_id)

    auth_url = f"{provider['issuer'].rstrip('/')}/authorize"
    params = {
        'response_type': 'code',
        'client_id': provider['client_id'],
        'redirect_uri': provider.get('redirect_uri', config.get('oauth_redirect_uri', '')),
        'scope': provider.get('scope', 'openid email profile'),
        'state': state,
        'code_challenge': _code_challenge(verifier),
        'code_challenge_method': 'S256',
    }
    redirect = f"{auth_url}?{urlencode(params)}"
    log.info('OAuth login redirect to %s (provider=%s)', auth_url, provider.get('slug', 'default'))
    return RedirectResponse(url=redirect, status_code=302)


async def oauth_callback(request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')

    if error:
        return unauthorized(f'OAuth provider returned error: {error}')
    if not code or not state:
        return api_error('MISSING_PARAMS', 'Missing code or state parameter', status=400)

    verifier, provider_id = await _verify_state(state)
    if verifier is None:
        return api_error('INVALID_STATE', 'State mismatch or expired', status=401)

    if provider_id:
        provider = await _get_provider_by_id(provider_id)
        if not provider:
            return api_error('PROVIDER_NOT_FOUND', 'OAuth provider not found', status=404)
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
    user, groups, _ = await _find_or_create_user(oauth_sub, email, name, provider)

    token = create_token(
        {'id': user['id'], 'admin': user.get('admin', False)},
        role=provider.get('default_role') or config.get('oauth_default_role'),
        permissions=None,
    )

    resp = ok({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user.get('username', email),
            'email': email,
        },
    })
    resp.set_cookie(key='token', value=token, httponly=True, samesite='strict', path='/api')
    return resp


async def oauth_token_exchange(request):
    body = await request.json()
    grant_type = body.get('grant_type', 'authorization_code')
    code = body.get('code', '')
    refresh_token = body.get('refresh_token', '')

    if grant_type == 'authorization_code' and code:
        verifier, provider_id = await _verify_state(request.query_params.get('state', ''))
        return api_error('INVALID_STATE', 'Use the callback endpoint for authorization_code flow', status=400)

    if grant_type == 'refresh_token' and refresh_token:
        payload = verify_token(refresh_token)
        if not payload:
            return unauthorized('Invalid or expired refresh token')
        user_data = {'id': payload['id'], 'admin': payload.get('admin', False)}
        role = payload.get('role')
        access, new_refresh = create_token_pair(user_data, role=role)
        return ok({
            'access_token': access,
            'refresh_token': new_refresh,
            'token_type': 'Bearer',
            'expires_in': 3600,
        })

    return api_error('UNSUPPORTED_GRANT', 'Unsupported grant_type', status=400)
