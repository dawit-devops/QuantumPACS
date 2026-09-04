"""Sprint S12 — Manager Dashboard API (S12-34) tests.

GET /api/ris/dashboard/kpi returns manager-facing KPIs: report TAT by
priority (p95), resource utilization, unbilled aging, and exam volume.
"""

import pytest

from unittest.mock import patch

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


def _make_dashboard_app(user=None):
    from api.ris_dashboard import (
        RisDashboardKpiHandler, DeptWorkloadHandler, DeptTatDrilldownHandler,
        DeptEquipmentUtilHandler, DeptStaffScheduleHandler,
    )

    return Starlette(
        routes=[
            Route('/ris/dashboard/kpi', endpoint=RisDashboardKpiHandler),
            Route('/ris/analytics/workload', endpoint=DeptWorkloadHandler),
            Route('/ris/analytics/tat-drilldown', endpoint=DeptTatDrilldownHandler),
            Route('/ris/analytics/equipment-util', endpoint=DeptEquipmentUtilHandler),
            Route('/ris/staff-schedule', endpoint=DeptStaffScheduleHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user or User({'id': 1, 'permissions': []}))],
    )


def _user(*perms):
    return User({'id': 1, 'permissions': list(perms)})


class _Conn:
    """In-memory asyncpg-like connection capturing SQL + results."""

    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchval = 0
        self._fetchrow = None

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchval(self, v):
        self._fetchval = v

    def set_fetchrow(self, row):
        self._fetchrow = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetchval(self, sql, *args):
        self.calls.append(('fetchval', sql, args))
        return self._fetchval

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


@pytest.fixture
def conn():
    return _Conn()


class TestRisDashboardKpiApi:
    """S12-34: GET /ris/dashboard/kpi — TAT, utilization, aging, volume."""

    def test_requires_report_read(self, conn):
        client = TestClient(_make_dashboard_app(_user()))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/dashboard/kpi')
        assert resp.status_code == 403

    def test_returns_kpi_structure(self, conn):
        # TAT by priority (percentile rows)
        conn.set_fetch([
            {'priority': 'stat', 'p95_seconds': 600.0},
            {'priority': 'routine', 'p95_seconds': 3600.0},
        ])
        # utilization ratio (fetchval on ris_appointments)
        # unbilled aging total
        conn.set_fetchrow({'total_unbilled': 3})
        # volume count (fetchval on worklist_entries)
        async def _fetchval(sql, *args):
            if 'ris_appointments' in sql:
                return 0.65
            if 'worklist_entries' in sql:
                return 42
            return 0
        conn.fetchval = _fetchval

        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ, Permission.BILLING_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/dashboard/kpi')
        assert resp.status_code == 200
        body = resp.json()
        assert body['tat_by_priority'][0]['priority'] == 'stat'
        assert body['tat_by_priority'][0]['p95_seconds'] == 600.0
        assert body['utilization'] == 0.65
        assert body['unbilled_aging']['total_unbilled'] == 3
        assert body['volume'] == 42

    def test_drill_down_returns_report_list(self, conn):
        # drill_down=true returns the raw TAT rows.
        conn.set_fetch([
            {'exam_id': 'e1', 'accession_number': 'ACC-1', 'priority': 'stat',
             'tat_seconds': 500.0},
        ])
        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ, Permission.BILLING_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/dashboard/kpi?drill_down=true')
        assert resp.status_code == 200
        body = resp.json()
        assert body['drill_down'][0]['accession_number'] == 'ACC-1'

class TestPriorAuthDashboardMix:
    """R2-01-09/15: status mix + approval rate on the manager dashboard."""

    def test_kpi_includes_prior_auth_mix(self, conn):
        conn.set_fetch([
            {'priority': 'stat', 'p95_seconds': 600.0},
        ])

        async def _fetchval(sql, *args):
            if 'ris_appointments' in sql:
                return 0.5
            if 'worklist_entries' in sql:
                return 7
            if ('ris_prior_auth_requests' in sql
                    and 'FILTER' in sql):
                return 0.955
            return 0

        conn.fetchval = _fetchval
        # second fetch call = prior-auth mix rows
        mix = [
            {'status': 'APPROVED', 'n': 21},
            {'status': 'PENDING', 'n': 3},
            {'status': 'DENIED', 'n': 1},
            {'status': 'EXPIRED', 'n': 1},
        ]
        calls = {'n': 0}

        async def _fetch(sql, *args):
            calls['n'] += 1
            if 'ris_prior_auth_requests' in sql and 'GROUP BY' in sql:
                return mix
            return [{'priority': 'stat', 'p95_seconds': 600.0}]

        conn.fetch = _fetch
        conn.set_fetchrow({'total_unbilled': 2})

        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/dashboard/kpi')
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['prior_auth']['mix'] == mix
        assert body['prior_auth']['approval_rate'] == 0.955


class TestDeptWorkload:
    """DM-01: Department workload distribution endpoint."""

    def test_requires_report_read(self, conn):
        client = TestClient(_make_dashboard_app(_user()))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/workload')
        assert resp.status_code == 403

    def test_returns_workload_structure(self, conn):
        conn.set_fetch([])
        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/workload')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert 'by_provider' in body
        assert 'by_modality' in body
        assert 'by_room' in body


class TestDeptTatDrilldown:
    """DM-02: TAT drill-down by provider."""

    def test_requires_report_read(self, conn):
        client = TestClient(_make_dashboard_app(_user()))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/tat-drilldown')
        assert resp.status_code == 403

    def test_returns_tat_structure(self, conn):
        conn.set_fetch([])
        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/tat-drilldown')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert 'by_provider' in body
        assert 'drill_down' in body

    def test_provider_drill_down(self, conn):
        calls = {'n': 0}

        async def _fetch(sql, *args):
            calls['n'] += 1
            return [{'provider': 'dr_jones', 'tat_seconds': 1200.0}]

        conn.fetch = _fetch
        client = TestClient(_make_dashboard_app(
            _user(Permission.REPORT_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/tat-drilldown?provider=dr_jones')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert len(body['drill_down']) == 1


class TestDeptEquipmentUtil:
    """DM-04: Equipment utilization endpoint."""

    def test_requires_equipment_read(self, conn):
        client = TestClient(_make_dashboard_app(_user()))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/equipment-util')
        assert resp.status_code == 403

    def test_returns_utilization_structure(self, conn):
        conn.set_fetch([])
        client = TestClient(_make_dashboard_app(
            _user(Permission.EQUIPMENT_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/analytics/equipment-util')
        assert resp.status_code == 200
        body = resp.json()['data']
        assert 'utilization' in body
        assert 'recent_downtime' in body


class TestDeptStaffSchedule:
    """DM-07: Staff schedule management endpoint."""

    def test_requires_schedule_read(self, conn):
        client = TestClient(_make_dashboard_app(_user()))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/staff-schedule')
        assert resp.status_code == 403

    def test_returns_schedule_list(self, conn):
        conn.set_fetch([])
        client = TestClient(_make_dashboard_app(
            _user(Permission.SCHEDULE_READ)))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/staff-schedule')
        assert resp.status_code == 200
        assert resp.json()['data'] == []
