from unittest.mock import AsyncMock, MagicMock, patch

from contextlib import ExitStack

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from api.users import RefreshToken
from api.tokens import create_token_pair, verify_token
from api.validate import validation_exception_handler, _ValidationException

SECRET = 'test-secret-key-for-refresh-token-test!!'


def _mock_auth_db(row, role):
    """Patch the refresh handler's DB re-read of user auth state."""
    mock_conn = AsyncMock()
    mock_conn.__aenter__.return_value = mock_conn
    mock_users = MagicMock()
    mock_users.return_value.get_user_row = AsyncMock(return_value=row)
    mock_users.return_value.get_user_role = AsyncMock(return_value=role)
    stack = ExitStack()
    stack.enter_context(patch('api.users.get_conn', return_value=mock_conn))
    stack.enter_context(patch('api.users.Users', mock_users))
    return stack


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
                    with _mock_auth_db(
                        {'id': 1, 'admin': True, 'status': 'active', 'token_version': 0},
                        ('super_admin', ['ALL']),
                    ):
                        resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            data = resp.json()
            assert 'access_token' in data
            # R2-LOW: refresh token is cookie-only — never in the JSON body.
            assert 'refresh_token' not in data
            assert data['token_type'] == 'Bearer'
            assert data['expires_in'] == 3600
            set_cookie = resp.headers.get('set-cookie', '')
            assert 'refresh_token=' in set_cookie
            assert 'HttpOnly' in set_cookie

            payload = verify_token(data['access_token'])
            assert payload['id'] == 1
            assert payload['admin'] is True
            assert payload['role'] == 'super_admin'
            assert payload['permissions'] == ['ALL']

    def test_refresh_rotates_tokens(self):
        access, refresh = self._token_pair()
        client = TestClient(self._make_app())

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    with _mock_auth_db(
                        {'id': 1, 'admin': True, 'status': 'active', 'token_version': 0},
                        ('super_admin', ['ALL']),
                    ):
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

    def test_refresh_returns_401_without_token(self):
        client = TestClient(self._make_app())
        resp = client.post('/api/auth/refresh', json={})
        assert resp.status_code == 401

    def test_refresh_via_http_only_cookie(self):
        access, refresh = self._token_pair()
        client = TestClient(self._make_app())
        client.cookies.set('refresh_token', refresh, path='/api/auth/refresh')

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    with _mock_auth_db(
                        {'id': 1, 'admin': True, 'status': 'active', 'token_version': 0},
                        ('super_admin', ['ALL']),
                    ):
                        resp = client.post('/api/auth/refresh', json={})

            assert resp.status_code == 200
            data = resp.json()
            assert 'access_token' in data
            # R2-LOW: refresh token is cookie-only — never in the JSON body.
            assert 'refresh_token' not in data
            set_cookie = resp.headers.get('set-cookie', '')
            assert 'refresh_token=' in set_cookie
            assert 'HttpOnly' in set_cookie
            # Cookie path covers /api/auth/refresh — matching the same
            # contract used by the password login endpoint.
            assert 'Path=/api/auth' in set_cookie

            payload = verify_token(data['access_token'])
            assert payload['id'] == 1

    def test_refresh_rotates_cookie_token(self):
        access, refresh = self._token_pair()
        client = TestClient(self._make_app())
        client.cookies.set('refresh_token', refresh, path='/api/auth/refresh')

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()) as mock_block:
                    with _mock_auth_db(
                        {'id': 1, 'admin': True, 'status': 'active', 'token_version': 0},
                        ('super_admin', ['ALL']),
                    ):
                        resp = client.post('/api/auth/refresh', json={})
                        assert resp.status_code == 200

            mock_block.assert_called_once_with(refresh)
            with patch('api.users.is_blocked', new=AsyncMock(return_value=True)):
                resp2 = client.post('/api/auth/refresh', json={})
                assert resp2.status_code == 401

    def test_refresh_preserves_tenant_claim(self):
        user = {'id': 3, 'admin': False, 'tenant': 'hospital-x'}
        access, refresh = self._token_pair(user)
        client = TestClient(self._make_app())

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    with _mock_auth_db(
                        {'id': 3, 'admin': False, 'tenant': 'hospital-x',
                         'status': 'active', 'token_version': 0},
                        ('receptionist', ['REGISTRATION_READ']),
                    ):
                        resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            payload = verify_token(resp.json()['access_token'])
            assert payload['tenant'] == 'hospital-x'
