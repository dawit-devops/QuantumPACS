"""RIS Care Plans API (CS5/CC-02) tests.

CARE_PLAN_WRITE was pre-granted to the coordinator but gated nothing; these
tests pin the new CRUD surface: GET gated by PATIENT_READ, POST/PATCH by
CARE_PLAN_WRITE, and task JSON serialization.
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
    from api.care_plans import CarePlanHandler, CarePlanDetailHandler
    return [
        ('/ris/care-plans', CarePlanHandler, ['GET', 'POST']),
        ('/ris/care-plans/{id}', CarePlanDetailHandler, ['PATCH']),
    ]


class TestCarePlanDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.care_plans import CarePlans
        conn.set_fetchrow({'id': 'cp-1', 'title': 'Post-op follow-up',
                           'status': 'active'})
        row = await CarePlans(conn).create(
            patient_id='8675309', title='Post-op follow-up',
            tasks=[{'label': 'Call patient', 'done': False}],
            responsible_provider='Dr. A', follow_up_at=None,
            notes='', by='1', tenant_id='default',
        )
        assert row['id'] == 'cp-1'
        assert any('INSERT INTO care_plans' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_filters_by_patient(self, conn):
        from db.care_plans import CarePlans
        conn.set_fetch([{'id': 'cp-1', 'patient_id': '8675309'}])
        rows = await CarePlans(conn).list('default', patient_id='8675309')
        assert rows[0]['id'] == 'cp-1'
        sql = conn.calls[-1][1]
        assert 'patient_id' in sql


class TestCarePlanApi:
    def test_get_requires_patient_read(self, conn):
        from api.care_plans import CarePlanHandler
        app = _make_app(_user(), [('/ris/care-plans', CarePlanHandler,
                                   ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.get('/ris/care-plans')
        assert resp.status_code == 403

    def test_post_requires_care_plan_write(self, conn):
        from api.care_plans import CarePlanHandler
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/care-plans', CarePlanHandler, ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.post('/ris/care-plans',
                           json={'patient_id': '1', 'title': 'X'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_creates_plan(self, conn):
        from api.care_plans import CarePlanHandler
        conn.set_fetchrow({'id': 'cp-1', 'patient_id': '8675309',
                           'title': 'Post-op', 'status': 'active'})
        app = _make_app(_user(Permission.CARE_PLAN_WRITE),
                        [('/ris/care-plans', CarePlanHandler, ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.care_plans.get_conn', return_value=conn):
            resp = client.post('/ris/care-plans',
                               json={'patient_id': '8675309',
                                     'title': 'Post-op',
                                     'tasks': [{'label': 'Call', 'done': False}],
                                     'status': 'active'})
        assert resp.status_code == 201
        body = resp.json()['data']
        assert body['title'] == 'Post-op'

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_patch_updates_existing_plan(self, conn):
        from api.care_plans import CarePlanDetailHandler
        conn.set_fetchrow({'id': 'cp-1', 'patient_id': '1', 'title': 'Old'})
        app = _make_app(_user(Permission.CARE_PLAN_WRITE),
                        [('/ris/care-plans/{id}', CarePlanDetailHandler,
                          ['PATCH'])])
        client = TestClient(app)
        with patch('api.care_plans.get_conn', return_value=conn):
            resp = client.patch(
                '/ris/care-plans/cp-1',
                json={'patient_id': '1', 'title': 'New', 'status': 'completed'})
        assert resp.status_code == 200
        assert resp.json()['status'] == 'updated'

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_patch_missing_plan_is_404(self, conn):
        from api.care_plans import CarePlanDetailHandler
        conn.set_fetchrow(None)
        app = _make_app(_user(Permission.CARE_PLAN_WRITE),
                        [('/ris/care-plans/{id}', CarePlanDetailHandler,
                          ['PATCH'])])
        client = TestClient(app)
        with patch('api.care_plans.get_conn', return_value=conn):
            resp = client.patch(
                '/ris/care-plans/nope',
                json={'patient_id': '1', 'title': 'X', 'status': 'active'})
        assert resp.status_code == 404

    def test_get_parses_jsonb_tasks_string(self, conn):
        # F6: asyncpg decodes jsonb to str by default — the list endpoint
        # must parse it back or the frontend crashes on tasks.filter.
        from api.care_plans import CarePlanHandler
        conn.set_fetch([{'id': 'cp-1', 'patient_id': '8675309',
                         'title': 'Post-op', 'status': 'active',
                         'tasks': '[{"label": "Call", "done": false}]'}])
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/care-plans', CarePlanHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.care_plans.get_conn', return_value=conn):
            resp = client.get('/ris/care-plans')
        assert resp.status_code == 200
        plan = resp.json()['data'][0]
        assert isinstance(plan['tasks'], list)
        assert plan['tasks'][0]['label'] == 'Call'

    def test_get_tasks_list_passthrough_and_bad_json_falls_back(self):
        from api.care_plans import _serialize
        # already-decoded list passes through; corrupt string degrades to []
        assert _serialize({'tasks': [{'label': 'A', 'done': True}]})[
            'tasks'] == [{'label': 'A', 'done': True}]
        assert _serialize({'tasks': 'not-json'})['tasks'] == []
