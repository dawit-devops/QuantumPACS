from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import create_token
from api.users import ChangePassword, Logout, RevokeToken
from api.validate import validation_exception_handler, _ValidationException

SECRET = 'test-secret-key-for-blocklist-tests!!'


def _fake_auth_middleware(user):
    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Middleware(FakeAuth)


class TestLogout:
    def _make_app(self):
        return Starlette(
            routes=[Route('/api/auth/logout', endpoint=Logout)],
        )

    def test_logout_blocklists_token(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout', headers={'X-Auth-Pacs': token})

        assert resp.status_code == 200
        assert resp.json() == {'message': 'Logged out'}
        mock_block.assert_awaited_once_with(token)

    def test_logout_without_token(self):
        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout')

        assert resp.status_code == 200
        mock_block.assert_not_awaited()

    def test_logout_with_bearer_token(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)

    def test_logout_with_cookie(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': False})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            client.cookies['token'] = token
            resp = client.post('/api/auth/logout')

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)


class TestChangePasswordBlocklist:
    def _make_app(self, user):
        return Starlette(
            routes=[Route('/api/change_password', endpoint=ChangePassword)],
            middleware=[_fake_auth_middleware(user)],
        )

    def test_change_password_blocklists_token(self):
        user = User({'id': 1, 'admin': True})
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app(user))

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.users.block_token', new=AsyncMock()) as mock_block,
            patch('api.users.Users') as mock_users,
        ):
            mock_users.return_value.change_password = AsyncMock(return_value=True)
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            with patch('api.users.get_conn', return_value=mock_conn):
                resp = client.post(
                    '/api/change_password',
                    json={'password': 'newpassword123'},
                    headers={'X-Auth-Pacs': token},
                )

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)

    def test_change_password_skip_blocklist_on_failure(self):
        user = User({'id': 1, 'admin': True})
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app(user))
        from exceptions import ApiException

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.users.block_token', new=AsyncMock()) as mock_block,
            patch('api.users.Users') as mock_users,
        ):
            mock_users.return_value.change_password = AsyncMock(
                side_effect=ApiException('Password error')
            )
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            with patch('api.users.get_conn', return_value=mock_conn):
                resp = client.post(
                    '/api/change_password',
                    json={'password': 'validpassword'},
                    headers={'X-Auth-Pacs': token},
                )

        assert resp.status_code == 400
        mock_block.assert_not_awaited()


class TestRevokeToken:
    def _make_app(self, user):
        return Starlette(
            routes=[Route('/api/auth/revoke', endpoint=RevokeToken)],
            middleware=[_fake_auth_middleware(user)],
        )

    def test_revoke_requires_admin(self):
        user = User({'id': 2, 'admin': False})
        client = TestClient(self._make_app(user))
        resp = client.post(
            '/api/auth/revoke',
            json={'token': 'some-jti'},
        )
        assert resp.status_code == 403

    def test_revoke_blocklists_provided_token(self):
        user = User({'id': 1, 'admin': True, 'permissions': ['USER_ADMIN']})
        client = TestClient(self._make_app(user))
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post(
                '/api/auth/revoke',
                json={'token': 'user-jwt-to-revoke'},
            )

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with('user-jwt-to-revoke')

    def test_revoke_returns_422_without_token_field(self):
        user = User({'id': 1, 'admin': True, 'permissions': ['USER_ADMIN']})
        app = Starlette(
            routes=[Route('/api/auth/revoke', endpoint=RevokeToken)],
            middleware=[_fake_auth_middleware(user)],
            exception_handlers={_ValidationException: validation_exception_handler},
        )
        client = TestClient(app)
        resp = client.post('/api/auth/revoke', json={})
        assert resp.status_code == 422


class TestBlockedTokenAuth:
    """Integration: a blocked token is rejected on subsequent requests."""

    def _make_app(self):
        app = Starlette(
            routes=[
                Route('/api/protected', endpoint=self._protected),
            ],
        )
        return app

    async def _protected(self, request):
        return JSONResponse({'ok': True})

    def test_blocked_token_returns_401(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        from starlette.middleware.authentication import AuthenticationMiddleware
        from api.auth import TokenAuth

        with patch('api.auth.config', {'secret': SECRET, 'cors_origins': '*'}):
            app = Starlette(
                routes=[
                    Route('/api/protected', endpoint=self._protected),
                ],
                middleware=[
                    Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                               on_error=TokenAuth.on_auth_error),
                ],
            )

            with patch('api.tokens.is_blocked', new=AsyncMock(return_value=True)):
                client = TestClient(app)
                resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})

            assert resp.status_code == 401
