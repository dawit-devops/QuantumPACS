from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from api.oauth import (
    _code_verifier, _code_challenge, oauth_login, oauth_callback, oidc_discovery,
    oidc_jwks, oauth_token_exchange,
)


class TestOidcDiscovery:
    def test_discovery_returns_valid_config(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        assert resp.status_code == 200
        data = resp.json()

        assert data['issuer'].endswith('/api')
        assert 'authorization_endpoint' in data
        assert 'token_endpoint' in data
        assert 'jwks_uri' in data
        assert 'code' in data['response_types_supported']
        assert 'S256' in data['code_challenge_methods_supported']
        assert 'authorization_code' in data['grant_types_supported']
        assert 'HS256' in data['id_token_signing_alg_values_supported']

    def test_discovery_endpoints_contain_base_url(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        data = resp.json()
        assert '/api/oauth/login' in data['authorization_endpoint']
        assert '/api/oauth/token' in data['token_endpoint']
        assert '/api/oauth/jwks' in data['jwks_uri']

    def test_discovery_includes_required_claims(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        claims = resp.json()['claims_supported']
        for claim in ('sub', 'iss', 'aud', 'exp', 'iat'):
            assert claim in claims


class TestOAuthUtils:
    def test_code_verifier_length(self):
        v = _code_verifier()
        assert len(v) >= 43
        assert len(v) <= 128

    def test_code_challenge_deterministic(self):
        v = _code_verifier()
        c1 = _code_challenge(v)
        c2 = _code_challenge(v)
        assert c1 == c2

    def test_code_challenge_differs_for_diff_verifiers(self):
        v1 = _code_verifier()
        v2 = _code_verifier()
        assert _code_challenge(v1) != _code_challenge(v2)


class MockClaims:
    def __init__(self, sub='user123', email='user@example.com', name='Test User'):
        self._data = {'sub': sub, 'email': email, 'name': name}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]


class TestOidcJwks:
    def test_jwks_endpoint_publishes_rsa_key(self):
        app = Starlette(routes=[Route('/api/oauth/jwks', endpoint=oidc_jwks)])
        client = TestClient(app)
        resp = client.get('/api/oauth/jwks')

        assert resp.status_code == 200
        keys = resp.json()['keys']
        assert len(keys) == 1
        key = keys[0]
        assert key['kty'] == 'RSA'
        assert key['use'] == 'sig'
        assert key['alg'] == 'RS256'
        assert key['kid']
        assert key['n']
        assert key['e'] == 'AQAB'

    def test_minted_tokens_verify_with_jwks_key(self):
        import jwt as pyjwt

        from api.jwt_keys import get_kid, get_public_key_pem
        from api.tokens import create_token

        with patch('api.tokens.config', {'secret': 'jwt-test-secret'}):
            token = create_token({'id': 1, 'admin': True}, expire={'minutes': 60})

        header = pyjwt.get_unverified_header(token)
        assert header['alg'] == 'RS256'
        assert header['kid'] == get_kid()

        payload = pyjwt.decode(token, get_public_key_pem(), algorithms=['RS256'])
        assert payload['id'] == 1

    def test_legacy_hs256_token_still_verifies_during_rotation(self):
        import time

        import jwt as pyjwt

        from api.tokens import verify_token

        with patch('api.tokens.config', {'secret': 'jwt-test-secret'}):
            legacy = pyjwt.encode(
                {'id': 1, 'admin': True, 'exp': int(time.time()) + 3600},
                'jwt-test-secret', algorithm='HS256',
            )
            payload = verify_token(legacy)

        assert payload['id'] == 1

    def test_jwks_is_reachable_without_auth(self):
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware

        from api.auth import TokenAuth

        app = Starlette(
            routes=[Route('/api/oauth/jwks', endpoint=oidc_jwks)],
            middleware=[
                Middleware(
                    AuthenticationMiddleware, backend=TokenAuth(),
                    on_error=TokenAuth.on_auth_error,
                ),
            ],
        )
        client = TestClient(app)

        resp = client.get('/api/oauth/jwks')
        assert resp.status_code == 200
        assert resp.json()['keys'][0]['alg'] == 'RS256'


class TestOAuthLogin:
    @pytest.mark.asyncio
    async def test_login_redirects_when_configured(self):
        request = MagicMock()
        request.query_params = {}
        cfg = {
            'oauth_issuer': 'https://accounts.google.com',
            'oauth_client_id': 'my-client-id',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_scope': 'openid email profile',
        }
        with patch('api.oauth.config', cfg):
            with patch('api.oauth._store_state', AsyncMock()):
                resp = await oauth_login(request)
        assert resp.status_code == 302
        location = resp.headers.get('location', '')
        assert 'accounts.google.com' in location
        assert 'response_type=code' in location
        assert 'code_challenge' in location

    @pytest.mark.asyncio
    async def test_login_returns_501_when_not_configured(self):
        request = MagicMock()
        request.query_params = {}
        cfg = {'oauth_issuer': '', 'oauth_client_id': ''}
        with patch('api.oauth.config', cfg):
            resp = await oauth_login(request)
        assert resp.status_code == 501


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_callback_with_error_returns_401(self):
        request = MagicMock()
        request.query_params = {'error': 'access_denied'}
        resp = await oauth_callback(request)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_400(self):
        request = MagicMock()
        request.query_params = {}
        resp = await oauth_callback(request)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_401(self):
        request = MagicMock()
        request.query_params = {'code': 'abc', 'state': 'bad'}
        with patch('api.oauth._verify_state', AsyncMock(return_value=(None, None))):
            resp = await oauth_callback(request)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_full_flow(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
            'oauth_default_role': 'radiologist',
        }

        tokens = {'id_token': 'fake-id-token'}
        claims = MockClaims(sub='oauth-user-1', email='dr@example.com', name='Dr Smith')

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.get_user_row = AsyncMock(return_value={
            'id': 42, 'admin': False, 'status': 'active', 'token_version': 0,
        })
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'radiologist', ['REPORT_READ'],
        ))

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        with patch('api.oauth._find_or_create_user', AsyncMock(return_value=(
                            {'id': 42, 'admin': False, 'username': 'dr'}, [],
                        ))):
                            with patch('api.oauth.get_conn', return_value=mock_conn):
                                with patch('api.oauth.Users', mock_users):
                                    with patch('api.oauth.create_token', return_value='qp-jwt-token') as mock_create_token:
                                        resp = await oauth_callback(request)

        assert resp.status_code == 200
        body = resp.body
        assert b'qp-jwt-token' in body
        assert b'token' in body
        kwargs = mock_create_token.call_args[1]
        assert kwargs.get('role') == 'radiologist'
        assert kwargs.get('permissions') == ['REPORT_READ']


class TestOAuthTokenExchange:
    def test_empty_body_returns_unsupported_grant(self):
        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        resp = client.post('/api/oauth/token', json={})

        assert resp.status_code == 400
        data = resp.json()
        assert data['error']['code'] == 'UNSUPPORTED_GRANT'
