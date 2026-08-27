"""Tests for DM-07 RIS staff time-off and coverage-gap endpoints.

Covers GET/POST /ris/staff-time-off, PATCH /ris/staff-time-off/{id}/status and
GET /ris/staff-time-off/coverage-gaps. The handler imports the RisStaffTimeOff
repo inside its methods, so we patch db.ris_staff_time_off.RisStaffTimeOff.
"""

from unittest.mock import patch
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission
from api.validate import _ValidationException, validation_exception_handler
from api.ris_dashboard import (
    StaffTimeOffHandler, StaffTimeOffStatusHandler, StaffCoverageGapsHandler,
)


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


def _app(user=None):
    return Starlette(
        routes=[
            Route('/ris/staff-time-off', endpoint=StaffTimeOffHandler),
            Route('/ris/staff-time-off/coverage-gaps', endpoint=StaffCoverageGapsHandler),
            Route('/ris/staff-time-off/{id}/status', endpoint=StaffTimeOffStatusHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user or User({'id': 1, 'permissions': []}))],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _user(*perms):
    return User({'id': 1, 'permissions': list(perms)})


class _ConnCtx:
    """Async context manager standing in for the pooled connection."""

    def __init__(self):
        self.sentinel = 'conn'

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetch(self, sql, *args):
        return []  # overridden per-test where used


class _FakeRepo:
    """In-memory substitute for RisStaffTimeOff that records calls."""

    def __init__(self):
        self.create_rows = []
        self.list_rows = []
        self.get_row = None
        self.update_row = None
        self.approved_rows = []
        self.fetch = None

    async def list_for_tenant(self, tenant_id, status=None):
        return self.list_rows

    async def create(self, data):
        self.created = data
        return {'id': 'to-1', **data, 'status': 'REQUESTED'}

    async def get(self, entry_id):
        return self.get_row

    async def update_status(self, entry_id, status):
        return self.update_row

    async def approved_in_range(self, tenant_id, start_date, end_date, modality=None):
        return self.approved_rows


def _setup(fake, user=None):
    """Patch get_conn to return a conn-ctx and repo construction to `fake`."""
    conn_ctx = _ConnCtx()
    app = _app(user)
    return patch('api.ris_dashboard.get_conn', return_value=conn_ctx), \
        patch('db.ris_staff_time_off.RisStaffTimeOff', lambda conn: fake), app


def test_list_requires_schedule_read():
    fake = _FakeRepo()
    gc, repo_patch, app = _setup(fake, _user())
    with gc, repo_patch:
        resp = TestClient(app).get('/ris/staff-time-off')
    assert resp.status_code == 403


def test_list_returns_time_off():
    fake = _FakeRepo()
    fake.list_rows = [
        {'id': 'to-1', 'staff_name': 'Jane', 'status': 'APPROVED',
         'start_date': '2026-09-01', 'end_date': '2026-09-03'},
    ]
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_READ))
    with gc, repo_patch:
        resp = TestClient(app).get('/ris/staff-time-off?status=APPROVED')
    assert resp.status_code == 200
    assert resp.json()['data'][0]['staff_name'] == 'Jane'


def test_create_requires_schedule_write():
    fake = _FakeRepo()
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_READ))
    with gc, repo_patch:
        resp = TestClient(app).post(
            '/ris/staff-time-off',
            json={'staff_id': 's1', 'start_date': '2026-09-01',
                  'end_date': '2026-09-02'},
        )
    assert resp.status_code == 403


def test_create_returns_created():
    fake = _FakeRepo()
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_WRITE))
    with gc, repo_patch:
        resp = TestClient(app).post(
            '/ris/staff-time-off',
            json={'staff_id': 's1', 'staff_name': 'Jane',
                  'modality': 'CT', 'start_date': '2026-09-01',
                  'end_date': '2026-09-02', 'reason': 'vacation'},
        )
    assert resp.status_code == 201
    body = resp.json()['data']
    assert body['staff_name'] == 'Jane'
    assert fake.created['tenant_id'] == 'default'
    assert body['status'] == 'REQUESTED'


def test_create_rejects_invalid_dates():
    fake = _FakeRepo()
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_WRITE))
    with gc, repo_patch:
        resp = TestClient(app).post(
            '/ris/staff-time-off',
            json={'staff_id': 's1', 'start_date': '2026-09-01'},
        )
    assert resp.status_code == 422


def test_status_update_requires_schedule_write():
    fake = _FakeRepo()
    fake.get_row = {'id': 'to-1', 'status': 'REQUESTED'}
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_READ))
    with gc, repo_patch:
        resp = TestClient(app).patch(
            '/ris/staff-time-off/to-1/status', json={'status': 'APPROVED'}
        )
    assert resp.status_code == 403


def test_status_update_approves():
    fake = _FakeRepo()
    fake.get_row = {'id': 'to-1', 'status': 'REQUESTED'}
    fake.update_row = {'id': 'to-1', 'status': 'APPROVED'}
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_WRITE))
    with gc, repo_patch:
        resp = TestClient(app).patch(
            '/ris/staff-time-off/to-1/status', json={'status': 'APPROVED'}
        )
    assert resp.status_code == 200
    assert resp.json()['data']['status'] == 'APPROVED'


def test_status_update_rejects_invalid_status():
    fake = _FakeRepo()
    fake.get_row = {'id': 'to-1', 'status': 'REQUESTED'}
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_WRITE))
    with gc, repo_patch:
        resp = TestClient(app).patch(
            '/ris/staff-time-off/to-1/status', json={'status': 'APPROVE'}
        )
    assert resp.status_code == 422


def test_status_update_404_when_missing():
    fake = _FakeRepo()
    fake.get_row = None
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_WRITE))
    with gc, repo_patch:
        resp = TestClient(app).patch(
            '/ris/staff-time-off/missing/status', json={'status': 'APPROVED'}
        )
    assert resp.status_code == 404


def test_coverage_gaps_requires_schedule_read():
    fake = _FakeRepo()
    gc, repo_patch, app = _setup(fake, _user())
    with gc, repo_patch:
        resp = TestClient(app).get(
            '/ris/staff-time-off/coverage-gaps?start_date=2026-09-01&end_date=2026-09-02'
        )
    assert resp.status_code == 403


def test_coverage_gaps_flags_technologist():
    from datetime import date

    fake = _FakeRepo()
    fake.approved_rows = [
        {'staff_id': 's1', 'staff_name': 'Jane', 'modality': 'CT',
         'start_date': date(2026, 9, 1), 'end_date': date(2026, 9, 1)},
    ]

    async def _fetch(sql, *args):
        return [{'exam_count': 2, 'modality': 'CT'}]

    fake.fetch = _fetch
    gc, repo_patch, app = _setup(fake, _user(Permission.SCHEDULE_READ))
    conn_ctx = _ConnCtx()
    conn_ctx.fetch = _fetch
    with patch('api.ris_dashboard.get_conn', return_value=conn_ctx), \
         patch('db.ris_staff_time_off.RisStaffTimeOff', lambda conn: fake):
        resp = TestClient(app).get(
            '/ris/staff-time-off/coverage-gaps?start_date=2026-09-01&end_date=2026-09-02'
        )
    assert resp.status_code == 200
    gaps = resp.json()['data']
    assert gaps and gaps[0]['staff_name'] == 'Jane'
    assert gaps[0]['scheduled_exams'] == 2
