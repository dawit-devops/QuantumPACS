from unittest.mock import AsyncMock, patch

import jwt
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import TokenAuth
from api.tokens import create_token, create_token_pair, verify_token
from api.users import Logout

SECRET = 'test-secret-key-for-auth-v2-tests!!'


async def _protected(request):
    return JSONResponse({
        'id': request.user.id,
        'admin': request.user.admin,
        'permissions': request.user.permissions,
        'role': request.user.role_slug,
        'tenant': request.user.tenant,
    })


def _make_token_app():
    return Starlette(
        routes=[Route('/api/protected', endpoint=_protected)],
        middleware=[
            Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                       on_error=TokenAuth.on_auth_error),
        ],
    )


class TestTokenClaims:
    def test_token_has_claims(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True}, expire={'minutes': 60})
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        assert payload['id'] == 1
        assert 'jti' in payload
        assert 'exp' in payload

    def test_token_with_role_and_permissions(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token(
                {'id': 2, 'admin': False},
                expire={'minutes': 60},
                role='technologist',
                permissions=['FILE_READ', 'FILE_WRITE'],
            )
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        assert payload['role'] == 'technologist'
        assert 'FILE_READ' in payload.get('permissions', [])

    def test_token_with_tenant_claim(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token(
                {'id': 3, 'admin': False, 'tenant': 'hospital-x'},
                expire={'minutes': 60},
            )
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        assert payload['tenant'] == 'hospital-x'

    def test_token_used_for_request(self):
        client = TestClient(_make_token_app())

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.Users') as mock_users,
        ):
            token = create_token({'id': 1, 'admin': True})
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})

        assert resp.status_code == 200
        data = resp.json()
        assert data['id'] == 1

    def test_expired_token_returns_401(self):
        import time
        with patch('api.tokens.config', {'secret': SECRET}):
            expired = jwt.encode(
                {'id': 1, 'admin': True, 'exp': int(time.time()) - 3600},
                SECRET, algorithm='HS256',
            )
        client = TestClient(_make_token_app())
        resp = client.get('/api/protected', headers={'X-Auth-Pacs': expired})
        assert resp.status_code == 401

    def test_blocked_token_returns_401(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        client = TestClient(_make_token_app())
        with patch('api.auth.is_blocked', new=AsyncMock(return_value=True)):
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 401

    def test_missing_auth_header_returns_401(self):
        client = TestClient(_make_token_app())
        resp = client.get('/api/protected')
        assert resp.status_code == 401


class TestQueryTokenRestriction:
    """Query-string credentials on HTTP are share keys only, never JWTs."""

    def _make_app(self):
        async def _file_endpoint(request):
            return JSONResponse({'ok': True})

        return Starlette(
            routes=[
                Route('/api/protected', endpoint=_protected),
                Route('/api/files/7/dicom', endpoint=_file_endpoint),
            ],
            middleware=[
                Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                           on_error=TokenAuth.on_auth_error),
            ],
        )

    def _mock_share_check(self, file_id):
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_files = AsyncMock()
        mock_files.check = AsyncMock(return_value=file_id)
        return mock_conn, mock_files

    def test_valid_jwt_in_query_param_rejected(self):
        """A valid JWT in ?token= must never authenticate on HTTP."""
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        mock_conn, mock_files = self._mock_share_check(None)
        client = TestClient(self._make_app())
        with (
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.SharedFiles', return_value=mock_files),
        ):
            resp = client.get('/api/protected', params={'token': token})
        assert resp.status_code == 401
        mock_files.check.assert_awaited_once()

    def test_share_key_in_query_param_allowed_on_shared_path(self):
        mock_conn, mock_files = self._mock_share_check(7)
        client = TestClient(self._make_app())
        with (
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.SharedFiles', return_value=mock_files),
        ):
            resp = client.get('/api/files/7/dicom', params={'token': 'share-key'})
        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    def test_share_key_in_query_param_rejected_on_other_paths(self):
        mock_conn, mock_files = self._mock_share_check(7)
        client = TestClient(self._make_app())
        with (
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.SharedFiles', return_value=mock_files),
        ):
            resp = client.get('/api/protected', params={'token': 'share-key'})
        assert resp.status_code == 401

    def test_jwt_in_cookie_still_authenticates(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        client = TestClient(self._make_app())
        client.cookies.set('token', token)
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            resp = client.get('/api/protected')
        assert resp.status_code == 200
        assert resp.json()['id'] == 1

    def test_jwt_in_query_param_rejected_even_for_shared_file_path(self):
        """JWT must not pass even on /api/files paths where share keys work."""
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        mock_conn, mock_files = self._mock_share_check(None)
        client = TestClient(self._make_app())
        with (
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.SharedFiles', return_value=mock_files),
        ):
            resp = client.get('/api/files/7/dicom', params={'token': token})
        assert resp.status_code == 401


class TestLogoutFlow:
    def _make_app(self):
        return Starlette(
            routes=[Route('/api/auth/logout', endpoint=Logout)],
        )

    def test_logout_and_subsequent_request_blocked(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout', headers={'X-Auth-Pacs': token})
            assert resp.status_code == 200
            mock_block.assert_awaited_once()


class TestRefreshFlow:
    def test_refresh_preserves_tenant_claim(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            user = {'id': 3, 'admin': False, 'tenant': 'hospital-x'}
            access, refresh = create_token_pair(user)

        app = Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
        )
        client = TestClient(app)

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            payload = verify_token(resp.json()['access_token'])
            assert payload['tenant'] == 'hospital-x'

    def test_refresh_rotates_and_old_used_again_blocked(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            access, refresh = create_token_pair({'id': 1, 'admin': True})

        app = Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
        )
        client = TestClient(app)

        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    resp1 = client.post('/api/auth/refresh', json={'refresh_token': refresh})
                    assert resp1.status_code == 200

            with patch('api.users.is_blocked', new=AsyncMock(return_value=True)):
                resp2 = client.post('/api/auth/refresh', json={'refresh_token': refresh})
                assert resp2.status_code == 401

    def test_expired_refresh_returns_401(self):
        import time
        from api.jwt_compat import encode as jwt_encode

        payload = {
            'jti': 'expired-jti', 'id': 1, 'type': 'refresh',
            'admin': True, 'exp': int(time.time()) - 3600,
        }
        with patch('config.config', {'secret': SECRET}):
            refresh = jwt_encode(payload, SECRET, algorithm='HS256')

        app = Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
        )
        client = TestClient(app)
        resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})
        assert resp.status_code == 401


from api.users import RefreshToken
