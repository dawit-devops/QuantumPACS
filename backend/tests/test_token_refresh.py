from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from api.users import RefreshToken
from api.tokens import create_token_pair, verify_token
from api.validate import validation_exception_handler, _ValidationException

SECRET = 'test-secret-key-for-refresh-token-test!!'


class TestRefreshEndpoint:
    def _token_pair(self, user=None):
        if user is None:
            user = {'id': 1, 'admin': True}
        with patch('api.tokens.config', {'secret': SECRET}):
            return create_token_pair(user)

    def _make_app(self):
        return Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
            exception_handlers={_ValidationException: validation_exception_handler},
        )

    def test_refresh_with_valid_token(self):
        access, refresh = self._token_pair()
        client = TestClient(self._make_app())

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            data = resp.json()
            assert 'access_token' in data
            assert 'refresh_token' in data
            assert data['token_type'] == 'Bearer'
            assert data['expires_in'] == 3600

            payload = verify_token(data['access_token'])
            assert payload['id'] == 1
            assert payload['admin'] is True

    def test_refresh_rotates_tokens(self):
        access, refresh = self._token_pair()
        client = TestClient(self._make_app())

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    resp1 = client.post('/api/auth/refresh', json={'refresh_token': refresh})
                    assert resp1.status_code == 200

            with patch('api.users.is_blocked', new=AsyncMock(return_value=True)):
                resp2 = client.post('/api/auth/refresh', json={'refresh_token': refresh})
                assert resp2.status_code == 401

    def test_refresh_with_expired_token(self):
        import time
        from api.jwt_compat import encode as jwt_encode

        refresh_payload = {
            'jti': 'test-jti-expired',
            'id': 1,
            'type': 'refresh',
            'admin': True,
            'exp': int(time.time()) - 3600,
        }
        with patch('config.config', {'secret': SECRET}):
            refresh = jwt_encode(refresh_payload, SECRET, algorithm='HS256')

        client = TestClient(self._make_app())
        resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})
        assert resp.status_code == 401

    def test_refresh_with_invalid_token(self):
        client = TestClient(self._make_app())
        resp = client.post('/api/auth/refresh', json={'refresh_token': 'not.a.token'})
        assert resp.status_code == 401

    def test_refresh_returns_422_without_token(self):
        client = TestClient(self._make_app())
        resp = client.post('/api/auth/refresh', json={})
        assert resp.status_code == 422

    def test_refresh_preserves_tenant_claim(self):
        user = {'id': 3, 'admin': False, 'tenant': 'hospital-x'}
        access, refresh = self._token_pair(user)
        client = TestClient(self._make_app())

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            payload = verify_token(resp.json()['access_token'])
            assert payload['tenant'] == 'hospital-x'
