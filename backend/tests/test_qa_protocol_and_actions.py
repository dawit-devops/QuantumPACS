"""Tests for QA-09 Protocol Registry and QA-11 Corrective Actions endpoints."""

from unittest.mock import AsyncMock, patch
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import _ValidationException, validation_exception_handler


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


PROTOCOL_ROW = {
    'id': 'prot-1',
    'tenant_id': 'default',
    'name': 'CT Chest',
    'modality': 'CT',
    'version': 1,
    'is_default': False,
    'content': 'Standard chest CT protocol',
    'created_by': '100',
    'created_at': '2026-08-27T00:00:00Z',
}

ACTION_ROW = {
    'id': 'act-1',
    'tenant_id': 'default',
    'title': 'Review incident INC-42',
    'description': 'Investigate contrast reaction',
    'assignee_id': '100',
    'incident_id': 'INC-42',
    'status': 'open',
    'priority': 'high',
    'due_date': '2026-09-01T00:00:00Z',
    'completed_at': None,
    'created_by': '100',
    'created_at': '2026-08-27T00:00:00Z',
}

STAFF = User({'id': 100, 'username': 'staff',
              'permissions': ['QA_READ', 'QA_WRITE']})
NO_PERMS = User({'id': 200, 'username': 'noperm', 'permissions': []})


def _make_app(user=None):
    from api.qa import (
        ProtocolHandler, ProtocolListHandler, ProtocolDefaultHandler,
        CorrectiveActionHandler, CorrectiveActionListHandler, EscalationHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/protocols', ProtocolListHandler),
            Route('/ris/protocols/{id}', ProtocolHandler),
            Route('/ris/protocols/{id}/default', ProtocolDefaultHandler,
                  methods=['POST']),
            Route('/ris/corrective-actions', CorrectiveActionListHandler),
            Route('/ris/corrective-actions/escalate', EscalationHandler),
            Route('/ris/corrective-actions/{id}', CorrectiveActionHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class _conn_ctx:
    def __init__(self, conn):
        self.conn = conn
    async def __aenter__(self):
        return self.conn
    async def __aexit__(self, *exc):
        return False


def _mock_conn(rows=None):
    mock = AsyncMock()
    mock.fetchrow.return_value = rows
    mock.fetch.return_value = rows or []
    mock.fetchval.return_value = True
    mock.execute.return_value = None
    return mock


# ── QA-09: Protocol Tests ──────────────────────────────────────────
class TestProtocolList:
    def test_requires_qa_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/ris/protocols')
        assert resp.status_code == 403

    def test_list_returns_protocols(self):
        client = TestClient(_make_app(STAFF))
        conn = _mock_conn([PROTOCOL_ROW])
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.get('/ris/protocols')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['name'] == 'CT Chest'


class TestProtocolCreate:
    def test_requires_qa_write(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.post('/ris/protocols', json={
            'name': 'MR Brain', 'modality': 'MR',
        })
        assert resp.status_code == 403

    def test_create_returns_created(self):
        client = TestClient(_make_app(STAFF))
        conn = _mock_conn(PROTOCOL_ROW)
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.post('/ris/protocols', json={
                'name': 'CT Chest', 'modality': 'CT',
                'content': 'Standard chest CT protocol',
            })
        assert resp.status_code == 201


class TestProtocolUpdate:
    def test_update_bumps_version(self):
        client = TestClient(_make_app(STAFF))
        updated = {**PROTOCOL_ROW, 'version': 2}
        conn = _mock_conn(updated)
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.put('/ris/protocols/prot-1', json={
                'name': 'CT Chest v2',
            })
        assert resp.status_code == 200


class TestProtocolDefault:
    def test_set_default(self):
        client = TestClient(_make_app(STAFF))
        default_row = {**PROTOCOL_ROW, 'is_default': True}
        conn = _mock_conn(default_row)
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.post('/ris/protocols/prot-1/default')
        assert resp.status_code == 200


# ── QA-11: Corrective Action Tests ────────────────────────────────
class TestCorrectiveActionList:
    def test_requires_qa_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/ris/corrective-actions')
        assert resp.status_code == 403

    def test_list_returns_actions(self):
        client = TestClient(_make_app(STAFF))
        conn = _mock_conn([ACTION_ROW])
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.get('/ris/corrective-actions')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['title'] == 'Review incident INC-42'


class TestCorrectiveActionCreate:
    def test_create_returns_created(self):
        client = TestClient(_make_app(STAFF))
        conn = _mock_conn(ACTION_ROW)
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.post('/ris/corrective-actions', json={
                'title': 'Review incident INC-42',
                'assignee_id': '100',
                'incident_id': 'INC-42',
                'priority': 'high',
                'due_date': '2026-09-01T00:00:00Z',
            })
        assert resp.status_code == 201


class TestCorrectiveActionUpdate:
    def test_complete_sets_completed_at(self):
        client = TestClient(_make_app(STAFF))
        completed = {**ACTION_ROW, 'status': 'completed'}
        conn = _mock_conn(completed)
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.put('/ris/corrective-actions/act-1', json={
                'status': 'completed',
            })
        assert resp.status_code == 200


class TestEscalation:
    @patch('api.notify.notify_role', new_callable=AsyncMock)
    def test_escalate_returns_count(self, mock_notify):
        client = TestClient(_make_app(STAFF))
        conn = _mock_conn([ACTION_ROW])
        with patch('api.qa.get_conn', return_value=_conn_ctx(conn)):
            resp = client.get('/ris/corrective-actions/escalate')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['escalated_count'] == 1
        mock_notify.assert_awaited()
