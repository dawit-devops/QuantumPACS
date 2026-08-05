from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.notifications import (
    NotificationsHandler, NotificationHandler,
    NotificationsReadAllHandler, NotificationsUnreadCountHandler,
)
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 42, 'permissions': ['FILE_READ']})

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


class TestNotificationsList:
    def _make_app(self, user=None):
        return _make_app([Route('/notifications', endpoint=NotificationsHandler)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'n1', 'user_id': 42, 'event_type': 'study.arrived',
             'title': 'Study arrived', 'body': 'CT Chest', 'link': '/studies/1',
             'read': False, 'created_at': '2026-07-29T00:00:00Z'},
        ])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/notifications?limit=10&offset=0')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1
        assert resp.json()['total'] == 1
        assert resp.json()['data'][0]['event_type'] == 'study.arrived'

    def test_list_empty(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/notifications')
        assert resp.status_code == 200
        assert resp.json()['data'] == []
        assert resp.json()['total'] == 0

    def test_missing_permission(self):
        user = User({'id': 42, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/notifications')
        assert resp.status_code == 403

    def test_dismiss_all(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/notifications')
        assert resp.status_code == 200


class TestNotificationSingle:
    def _make_app(self, user=None):
        return _make_app([Route('/notifications/{id}', endpoint=NotificationHandler)], user)

    def test_mark_read(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/notifications/n1')
        assert resp.status_code == 200

    def test_dismiss(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/notifications/n1')
        assert resp.status_code == 200


class TestNotificationsReadAll:
    def _make_app(self, user=None):
        return _make_app([Route('/notifications/read-all', endpoint=NotificationsReadAllHandler)], user)

    def test_mark_all_read(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/notifications/read-all')
        assert resp.status_code == 200


class TestNotificationsUnreadCount:
    def _make_app(self, user=None):
        return _make_app([Route('/notifications/unread-count', endpoint=NotificationsUnreadCountHandler)], user)

    def test_unread_count(self):
        mock_conn = _mock_conn()
        mock_conn.unread_count = AsyncMock(return_value=5)
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/notifications/unread-count')
        assert resp.status_code == 200
        assert resp.json()['count'] == 0

    def test_unread_count_with_data(self):
        mock_conn = _mock_conn()
        mock_conn.fetchval = AsyncMock(return_value=3)
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/notifications/unread-count')
        assert resp.status_code == 200
        assert resp.json()['count'] == 3
