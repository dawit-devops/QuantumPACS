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
from api.tokens import create_token
from config import config
from db.conn import get_conn
from db.users import Users
from log import get_logger

log = get_logger(__name__)

_JWKS_CLIENT = None


def _get_jwks_client():
    global _JWKS_CLIENT
    if _JWKS_CLIENT is None:
        jwks_uri = config.get('oauth_jwks_uri', '')
        if jwks_uri:
            _JWKS_CLIENT = PyJWKClient(jwks_uri, cache_keys=True)
    return _JWKS_CLIENT


def _code_verifier():
    return secrets.token_urlsafe(64)


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


async def _store_state(state, verifier):
    try:
        from api.redis_client import get_client as get_redis
        redis = await get_redis()
        await redis.set(f'oauth_state:{state}', verifier, ex=300)
    except Exception:
        log.warning('Failed to store OAuth state in Redis')


async def _verify_state(state):
    try:
        from api.redis_client import get_client as get_redis
        redis = await get_redis()
        verifier = await redis.get(f'oauth_state:{state}')
        if verifier:
            await redis.delete(f'oauth_state:{state}')
            return verifier.decode() if isinstance(verifier, bytes) else verifier
    except Exception:
        log.warning('Failed to verify OAuth state from Redis')
    return None


async def _exchange_code(code, verifier):
    token_url = f"{config['oauth_issuer'].rstrip('/')}/token"
    if config.get('oauth_jwks_uri'):
        token_url = config['oauth_token_url'] or token_url

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': config['oauth_redirect_uri'],
        'client_id': config['oauth_client_id'],
        'client_secret': config['oauth_client_secret'],
    }
    if verifier:
        data['code_verifier'] = verifier

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            log.error('Token exchange failed: %s %s', resp.status_code, resp.text)
            return None
        return resp.json()


def _verify_id_token(id_token):
    client = _get_jwks_client()
    if client is None:
        log.error('JWKS client not configured')
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=['RS256'],
            audience=config['oauth_client_id'],
            issuer=config['oauth_issuer'],
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


async def _find_or_create_user(oauth_sub, email, name):
    async with get_conn() as conn:
        q = Users(conn).select('*').where(Users.table.oauth_sub == oauth_sub)
        user = await conn.fetchrow(str(q))
        if user:
            return dict(user)

        role_slug = config.get('oauth_default_role', 'cashier')
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
        return {'id': new_id, 'username': username, 'admin': False, 'role_id': role_id,
                'oauth_sub': oauth_sub, 'email': email}


def _base_url(request):
    return f"{request.url.scheme}://{request.url.hostname}:{request.url.port}"


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
    issuer = config.get('oauth_issuer', '')
    client_id = config.get('oauth_client_id', '')
    if not issuer or not client_id:
        return api_error('OAUTH_NOT_CONFIGURED', 'OAuth is not configured', status=501)

    verifier = _code_verifier()
    state = secrets.token_urlsafe(32)
    await _store_state(state, verifier)

    auth_url = f"{issuer.rstrip('/')}/authorize"
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': config['oauth_redirect_uri'],
        'scope': config.get('oauth_scope', 'openid email profile'),
        'state': state,
        'code_challenge': _code_challenge(verifier),
        'code_challenge_method': 'S256',
    }
    redirect = f"{auth_url}?{urlencode(params)}"
    log.info('OAuth login redirect: %s', redirect)
    return RedirectResponse(url=redirect, status_code=302)


async def oauth_callback(request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')

    if error:
        return unauthorized(f'OAuth provider returned error: {error}')
    if not code or not state:
        return api_error('MISSING_PARAMS', 'Missing code or state parameter', status=400)

    verifier = await _verify_state(state)
    if verifier is None:
        return api_error('INVALID_STATE', 'State mismatch or expired — try logging in again', status=401)

    tokens = await _exchange_code(code, verifier)
    if tokens is None:
        return api_error('TOKEN_EXCHANGE_FAILED', 'Failed to exchange authorization code', status=502)

    id_token = tokens.get('id_token')
    if not id_token:
        return api_error('MISSING_ID_TOKEN', 'IdP did not return an id_token', status=502)

    claims = _verify_id_token(id_token)
    if claims is None:
        return api_error('INVALID_ID_TOKEN', 'id_token verification failed', status=401)

    oauth_sub = claims.get('sub')
    email = claims.get('email') or claims.get('preferred_username', '')
    name = claims.get('name', '')
    user = await _find_or_create_user(oauth_sub, email, name)

    token = create_token(
        {'id': user['id'], 'admin': user.get('admin', False)},
        role=config.get('oauth_default_role'),
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
    resp.set_cookie(
        key='token',
        value=token,
        httponly=True,
        samesite='strict',
        path='/api',
    )
    return resp
