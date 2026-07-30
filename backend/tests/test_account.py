from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.account import ProfileHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['FILE_READ'], 'tenant': 'default', 'role_slug': 'admin'})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(module, mock_conn):
    return patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestProfile:
    def _make_app(self, user=None):
        return _make_app([Route('/account/profile', endpoint=ProfileHandler)], user)

    def test_get_profile(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'username': 'admin', 'email': 'admin@test.com',
            'created': '2026-01-01T00:00:00', 'role_id': 99, 'last_login': None,
        })
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.get = AsyncMock(return_value={'name': 'Admin', 'slug': 'admin'})
        mock_conn.get_by_slug = AsyncMock(return_value={'name': 'Default Tenant'})
        with _patch_get_conn('api.account', mock_conn), \
             patch('api.account.Roles') as mock_roles, \
             patch('api.account.Tenants') as mock_tenants:
            mock_roles.return_value.get = AsyncMock(return_value={'name': 'Admin', 'slug': 'admin'})
            mock_tenants.return_value.get_by_slug = AsyncMock(return_value={'name': 'Default Tenant'})
            client = TestClient(self._make_app())
            resp = client.get('/account/profile')
        assert resp.status_code == 200
        body = resp.json()
        assert body['username'] == 'admin'
        assert body['email'] == 'admin@test.com'
        assert body['role'] == 'admin'
        assert body['tenant'] == 'default'

    def test_get_profile_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.account', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/account/profile')
        assert resp.status_code == 404

    def test_update_profile(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.account', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/account/profile', json={'email': 'new@test.com'})
        assert resp.status_code == 200
        assert resp.json()['message'] == 'Profile updated'
