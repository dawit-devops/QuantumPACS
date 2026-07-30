from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.oauth_providers import OAuthProvidersHandler, OAuthProviderHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['TENANT_ADMIN']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
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


class TestOAuthProvidersHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/oauth/providers', endpoint=OAuthProvidersHandler)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
             'enabled': True, 'created_at': '2026-01-01', 'updated_at': '2026-01-01'},
        ])
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/oauth/providers')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1

    def test_list_empty(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/oauth/providers')
        assert resp.status_code == 200
        assert resp.json()['data'] == []

    def test_list_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/oauth/providers')
        assert resp.status_code == 403

    def test_create(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.fetchval = AsyncMock(return_value='new-p1')
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/oauth/providers', json={
                'issuer': 'https://idp.example.com',
                'client_id': 'my-client',
            })
        assert resp.status_code == 201
        assert resp.json()['id'] == 'new-p1'

    def test_create_duplicate_issuer(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'p1', 'issuer': 'https://idp.example.com',
        })
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/oauth/providers', json={
                'issuer': 'https://idp.example.com',
                'client_id': 'my-client',
            })
        assert resp.status_code == 200
        assert 'error' in resp.json()

    def test_create_missing_required(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/oauth/providers', json={'issuer': 'https://idp.example.com'})
        assert resp.status_code == 422

    def test_create_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.post('/oauth/providers', json={
            'issuer': 'https://idp.example.com',
            'client_id': 'my-client',
        })
        assert resp.status_code == 403


class TestOAuthProviderHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/oauth/providers/{id}', endpoint=OAuthProviderHandler)], user)

    def test_get_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
            'enabled': True, 'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        })
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/oauth/providers/p1')
        assert resp.status_code == 200

    def test_get_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/oauth/providers/nonexistent')
        assert resp.status_code == 404

    def test_get_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/oauth/providers/p1')
        assert resp.status_code == 403

    def test_update(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
        })
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/oauth/providers/p1', json={'client_id': 'new-client'})
        assert resp.status_code == 200

    def test_update_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/oauth/providers/nonexistent', json={'client_id': 'new-client'})
        assert resp.status_code == 404

    def test_update_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.put('/oauth/providers/p1', json={'client_id': 'new-client'})
        assert resp.status_code == 403

    def test_delete(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'p1', 'issuer': 'https://idp.example.com', 'client_id': 'abc',
        })
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/oauth/providers/p1')
        assert resp.status_code == 200

    def test_delete_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.oauth_providers', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/oauth/providers/nonexistent')
        assert resp.status_code == 404

    def test_delete_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.delete('/oauth/providers/p1')
        assert resp.status_code == 403
