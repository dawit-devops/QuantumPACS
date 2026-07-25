from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.oauth import (
    _code_verifier, _code_challenge, _verify_id_token,
    oauth_login, oauth_callback,
)


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


class TestOAuthLogin:
    @pytest.mark.asyncio
    async def test_login_redirects_when_configured(self):
        request = MagicMock()
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
        with patch('api.oauth._verify_state', AsyncMock(return_value=None)):
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

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value='code-verifier')):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        with patch('api.oauth._find_or_create_user', AsyncMock(return_value={
                            'id': 42, 'admin': False, 'username': 'dr'
                        })):
                            with patch('api.oauth.create_token', return_value='qp-jwt-token'):
                                resp = await oauth_callback(request)

        assert resp.status_code == 200
        body = resp.body
        assert b'qp-jwt-token' in body
        assert b'token' in body
