from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.logs import LogsHandler, LogEventTypesHandler, LogActorsHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['LOG_READ', 'TENANT_READ']})

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


class TestLogs:
    def _make_app(self, user=None):
        return _make_app([Route('/logs', endpoint=LogsHandler)], user)

    def test_query(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'l1', 'event_type': 'file.upload', 'actor': 'admin',
             'description': 'Uploaded file', 'created_at': '2026-07-29T00:00:00Z',
             'tenant': 'default', 'ip_address': '127.0.0.1'},
        ])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs?limit=50')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1
        assert resp.json()['total'] == 1

    def test_query_empty(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs')
        assert resp.status_code == 200
        assert resp.json()['data'] == []
        assert resp.json()['total'] == 0
        assert resp.json()['has_more'] is False

    def test_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/logs')
        assert resp.status_code == 403

    def test_query_with_event_filter(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs?event_type=file.upload&limit=10')
        assert resp.status_code == 200

    def test_query_clamps_limit(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with _patch_get_conn('api.logs', mock_conn):
            resp = TestClient(self._make_app()).get('/logs?limit=999')
        assert resp.status_code == 200

    def test_query_requires_tenant_read_for_tenant_filter(self):
        user = User({'id': 1, 'permissions': ['LOG_READ']})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/logs?tenant=other')
        assert resp.status_code == 403


class TestLogEventTypes:
    def _make_app(self, user=None):
        return _make_app([Route('/logs/event-types', endpoint=LogEventTypesHandler)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'event_type': 'file.upload'},
        ])
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs/event-types')
        assert resp.status_code == 200
        assert 'data' in resp.json()


class TestLogActors:
    def _make_app(self, user=None):
        return _make_app([Route('/logs/actors', endpoint=LogActorsHandler)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'username': 'admin'},
        ])
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs/actors')
        assert resp.status_code == 200
        assert 'data' in resp.json()

    def test_search(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'username': 'admin'},
        ])
        with _patch_get_conn('api.logs', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/logs/actors?search=admin')
        assert resp.status_code == 200
