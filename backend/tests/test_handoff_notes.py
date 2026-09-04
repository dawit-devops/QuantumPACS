"""RIS Handoff Notes API (CC-08) tests.

Handoff notes: PATIENT_READ lists, PATIENT_WRITE creates + marks read.
Tests pin the permission gates, list filters (patient / unread), create
serialization, and the read-state transition.
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user, handlers):
    from starlette.exceptions import HTTPException
    from api.validate import validation_exception_handler, _ValidationException

    def _http_exception(request, exc):
        from starlette.responses import JSONResponse
        return JSONResponse(
            {'error': exc.detail if hasattr(exc, 'detail') else ''},
            status_code=exc.status_code,
        )

    return Starlette(
        routes=[Route(path, endpoint=h, methods=m) for path, h, m in handlers],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _user(*perms, tenant='default'):
    return User({'id': 1, 'permissions': list(perms), 'tenant': tenant})


class _Conn:
    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchrow = None

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchrow(self, row):
        self._fetchrow = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


@pytest.fixture
def conn():
    return _Conn()


def _handlers():
    from api.handoff_notes import HandoffNotesHandler, HandoffNoteReadHandler
    return [
        ('/ris/handoff-notes', HandoffNotesHandler, ['GET', 'POST']),
        ('/ris/handoff-notes/{id}/read', HandoffNoteReadHandler, ['PATCH']),
    ]


class TestHandoffNoteDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.ris_handoff import HandoffNotes
        conn.set_fetchrow({'id': 'hn-1', 'patient_id': '8675309',
                           'note': 'Call back', 'priority': 'high'})
        row = await HandoffNotes(conn).create(
            patient_id='8675309', note='Call back', priority='high',
            by='1', tenant_id='default',
        )
        assert row['id'] == 'hn-1'
        assert any('INSERT INTO ris_handoff_notes' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_filters_by_patient(self, conn):
        from db.ris_handoff import HandoffNotes
        conn.set_fetch([{'id': 'hn-1', 'patient_id': '8675309'}])
        rows = await HandoffNotes(conn).list('default', patient_id='8675309')
        assert rows[0]['id'] == 'hn-1'
        sql = conn.calls[-1][1]
        assert 'patient_id' in sql

    @pytest.mark.asyncio
    async def test_list_unread_only(self, conn):
        from db.ris_handoff import HandoffNotes
        conn.set_fetch([{'id': 'hn-1', 'is_read': False}])
        rows = await HandoffNotes(conn).list('default', unread_only=True)
        assert rows[0]['id'] == 'hn-1'
        sql = conn.calls[-1][1]
        assert 'is_read' in sql


class TestHandoffNoteApi:
    def test_get_requires_patient_read(self, conn):
        app = _make_app(_user(), _handlers())
        client = TestClient(app)
        resp = client.get('/ris/handoff-notes')
        assert resp.status_code == 403

    def test_post_requires_patient_write(self, conn):
        app = _make_app(_user(Permission.PATIENT_READ), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/handoff-notes',
                           json={'patient_id': '1', 'note': 'X'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_creates_note(self, conn):
        conn.set_fetchrow({'id': 'hn-1', 'patient_id': '8675309',
                           'note': 'Call back', 'priority': 'urgent',
                           'is_read': False})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.handoff_notes.get_conn', return_value=conn):
            resp = client.post('/ris/handoff-notes',
                               json={'patient_id': '8675309',
                                     'note': 'Call back',
                                     'priority': 'urgent'})
        assert resp.status_code == 201
        body = resp.json()['data']
        assert body['note'] == 'Call back'
        assert body['priority'] == 'urgent'

    def test_post_rejects_bad_priority(self, conn):
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/handoff-notes',
                           json={'patient_id': '1', 'note': 'X',
                                 'priority': 'blitz'})
        assert resp.status_code == 422

    def test_mark_read_requires_patient_write(self, conn):
        app = _make_app(_user(Permission.PATIENT_READ), _handlers())
        client = TestClient(app)
        resp = client.patch('/ris/handoff-notes/hn-1/read')
        assert resp.status_code == 403

    def test_mark_read_updates_note(self, conn):
        conn.set_fetchrow({'id': 'hn-1', 'patient_id': '8675309',
                           'is_read': False})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.handoff_notes.get_conn', return_value=conn):
            resp = client.patch('/ris/handoff-notes/hn-1/read')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'read'
        assert any('is_read = true' in c[1] for c in conn.calls)

    def test_mark_read_missing_note_is_404(self, conn):
        conn.set_fetchrow(None)
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.handoff_notes.get_conn', return_value=conn):
            resp = client.patch('/ris/handoff-notes/nope/read')
        assert resp.status_code == 404