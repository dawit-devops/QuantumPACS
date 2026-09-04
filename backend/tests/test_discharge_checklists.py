"""RIS Discharge Planning Checklist API (CC-06) tests.

Checklists: PATIENT_READ lists, PATIENT_WRITE creates + updates. Tests
pin permission gates, default template items on create, item JSON
serialization, status transitions, and list filters.
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
    from api.discharge import (
        DischargeChecklistsHandler, DischargeChecklistDetailHandler,
    )
    return [
        ('/ris/discharge-checklists', DischargeChecklistsHandler, ['GET', 'POST']),
        ('/ris/discharge-checklists/{id}', DischargeChecklistDetailHandler,
         ['PATCH']),
    ]


class TestDischargeChecklistDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.ris_discharge import DischargeChecklists
        conn.set_fetchrow({'id': 'dc-1', 'patient_id': '8675309',
                           'title': 'Discharge Checklist', 'status': 'open'})
        row = await DischargeChecklists(conn).create(
            patient_id='8675309', title='Discharge Checklist',
            items=[{'label': 'Follow-up scheduled', 'done': False}],
            notes='', by='1', tenant_id='default',
        )
        assert row['id'] == 'dc-1'
        assert any('INSERT INTO ris_discharge_checklists' in c[1]
                   for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_filters_by_patient(self, conn):
        from db.ris_discharge import DischargeChecklists
        conn.set_fetch([{'id': 'dc-1', 'patient_id': '8675309'}])
        rows = await DischargeChecklists(conn).list('default',
                                                    patient_id='8675309')
        assert rows[0]['id'] == 'dc-1'
        sql = conn.calls[-1][1]
        assert 'patient_id' in sql


class TestDischargeChecklistApi:
    def test_get_requires_patient_read(self, conn):
        app = _make_app(_user(), _handlers())
        client = TestClient(app)
        resp = client.get('/ris/discharge-checklists')
        assert resp.status_code == 403

    def test_post_requires_patient_write(self, conn):
        app = _make_app(_user(Permission.PATIENT_READ), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/discharge-checklists',
                           json={'patient_id': '1'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_creates_with_default_template_items(self, conn):
        conn.set_fetchrow({'id': 'dc-1', 'patient_id': '8675309',
                           'title': 'Discharge Checklist', 'status': 'open',
                           'items': [
                               {'label': 'Follow-up appointment scheduled',
                                'done': False},
                               {'label': 'Medication reconciliation',
                                'done': False},
                               {'label': 'Patient education provided',
                                'done': False},
                           ]})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.discharge.get_conn', return_value=conn):
            resp = client.post('/ris/discharge-checklists',
                               json={'patient_id': '8675309'})
        assert resp.status_code == 201
        body = resp.json()['data']
        assert body['status'] == 'open'
        assert len(body['items']) == 3
        assert body['items'][0]['label'] == 'Follow-up appointment scheduled'

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_accepts_custom_items(self, conn):
        conn.set_fetchrow({'id': 'dc-1', 'patient_id': '8675309',
                           'title': 'DC', 'status': 'open',
                           'items': [{'label': 'Custom item', 'done': True}]})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.discharge.get_conn', return_value=conn):
            resp = client.post('/ris/discharge-checklists', json={
                'patient_id': '8675309',
                'items': [{'label': 'Custom item', 'done': True}],
            })
        assert resp.status_code == 201
        assert resp.json()['data']['items'][0]['label'] == 'Custom item'

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_patch_updates_status_and_items(self, conn):
        conn.set_fetchrow({'id': 'dc-1', 'patient_id': '1', 'status': 'open'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.discharge.get_conn', return_value=conn):
            resp = client.patch('/ris/discharge-checklists/dc-1', json={
                'status': 'completed',
                'items': [
                    {'label': 'Follow-up appointment scheduled', 'done': True},
                    {'label': 'Medication reconciliation', 'done': True},
                    {'label': 'Patient education provided', 'done': True},
                ],
            })
        assert resp.status_code == 200
        assert resp.json()['status'] == 'updated'
        assert any('items = $3' in c[1] for c in conn.calls)

    def test_patch_rejects_bad_status(self, conn):
        conn.set_fetchrow({'id': 'dc-1', 'patient_id': '1', 'status': 'open'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.discharge.get_conn', return_value=conn):
            resp = client.patch('/ris/discharge-checklists/dc-1', json={
                'status': 'invalid',
            })
        assert resp.status_code == 422

    def test_patch_missing_is_404(self, conn):
        conn.set_fetchrow(None)
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.discharge.get_conn', return_value=conn):
            resp = client.patch('/ris/discharge-checklists/nope', json={
                'status': 'open',
            })
        assert resp.status_code == 404