"""RIS Referral Tracking API (CC-05) tests.

Referrals: PATIENT_READ lists, PATIENT_WRITE creates + updates.
Tests pin permission gates, create serialization, status transitions,
and list filters by patient/status.
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
    from api.referrals import ReferralsHandler, ReferralDetailHandler
    return [
        ('/ris/referrals', ReferralsHandler, ['GET', 'POST']),
        ('/ris/referrals/{id}', ReferralDetailHandler, ['PATCH']),
    ]


class TestReferralDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.ris_referrals import Referrals
        conn.set_fetchrow({'id': 'ref-1', 'patient_id': '8675309',
                           'to_specialist': 'Dr. Smith',
                           'status': 'pending'})
        row = await Referrals(conn).create(
            patient_id='8675309', from_provider='Dr. Jones',
            to_specialist='Dr. Smith', specialty='Cardiology',
            order_id='', report_id='', notes='', by='1',
            tenant_id='default',
        )
        assert row['id'] == 'ref-1'
        assert any('INSERT INTO ris_referrals' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_filters_by_patient(self, conn):
        from db.ris_referrals import Referrals
        conn.set_fetch([{'id': 'ref-1', 'patient_id': '8675309'}])
        rows = await Referrals(conn).list('default', patient_id='8675309')
        assert rows[0]['id'] == 'ref-1'
        sql = conn.calls[-1][1]
        assert 'patient_id' in sql

    @pytest.mark.asyncio
    async def test_list_filters_by_status(self, conn):
        from db.ris_referrals import Referrals
        conn.set_fetch([{'id': 'ref-1', 'status': 'accepted'}])
        rows = await Referrals(conn).list('default', status='accepted')
        assert rows[0]['id'] == 'ref-1'
        sql = conn.calls[-1][1]
        assert 'status' in sql


class TestReferralApi:
    def test_get_requires_patient_read(self, conn):
        app = _make_app(_user(), _handlers())
        client = TestClient(app)
        resp = client.get('/ris/referrals')
        assert resp.status_code == 403

    def test_post_requires_patient_write(self, conn):
        app = _make_app(_user(Permission.PATIENT_READ), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/referrals',
                           json={'patient_id': '1', 'to_specialist': 'Dr. X'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_creates_referral(self, conn):
        conn.set_fetchrow({'id': 'ref-1', 'patient_id': '8675309',
                           'to_specialist': 'Dr. Smith',
                           'specialty': 'Cardiology',
                           'status': 'pending'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.referrals.get_conn', return_value=conn):
            resp = client.post('/ris/referrals', json={
                'patient_id': '8675309',
                'from_provider': 'Dr. Jones',
                'to_specialist': 'Dr. Smith',
                'specialty': 'Cardiology',
                'notes': 'Routine consult',
            })
        assert resp.status_code == 201
        body = resp.json()['data']
        assert body['to_specialist'] == 'Dr. Smith'
        assert body['status'] == 'pending'

    def test_post_rejects_bad_status(self, conn):
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/referrals', json={
            'patient_id': '1', 'to_specialist': 'Dr. X',
            'status': 'invalid',
        })
        assert resp.status_code == 422

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_patch_updates_status(self, conn):
        conn.set_fetchrow({'id': 'ref-1', 'patient_id': '1',
                           'status': 'pending'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.referrals.get_conn', return_value=conn):
            resp = client.patch('/ris/referrals/ref-1', json={
                'status': 'accepted', 'notes': 'Scheduled',
            })
        assert resp.status_code == 200
        assert resp.json()['status'] == 'updated'
        assert any('status = $2' in c[1] for c in conn.calls)

    def test_patch_missing_is_404(self, conn):
        conn.set_fetchrow(None)
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.referrals.get_conn', return_value=conn):
            resp = client.patch('/ris/referrals/nope', json={
                'status': 'accepted',
            })
        assert resp.status_code == 404