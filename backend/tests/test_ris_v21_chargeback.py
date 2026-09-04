"""v2.1 R2-06-04/05 — per-site chargeback aggregation + manager parity.

Bookings stamp requesting_tenant (R2-03-08); nothing aggregated it. This
suite drives the servicing-site view: which external sites booked here,
in the window, and the manager-dashboard parity fields (chargeback rows
+ claim denial rate).
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.scheduling import RisChargebackHandler

    return Starlette(
        routes=[Route('/ris/scheduling/chargeback',
                      endpoint=RisChargebackHandler)],
        middleware=[Middleware(_FakeAuth,
                               user=user or User({'id': 5, 'tenant': 'main-hospital',
                                                  'permissions': ['BILLING_READ'],
                                                  'admin': True}))],
    )


class _Conn:
    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchval = 0

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchval(self, v):
        self._fetchval = v

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchval(self, sql, *args):
        return self._fetchval


_ROWS = [
    {'requesting_tenant': 'clinic-north', 'bookings': 12},
    {'requesting_tenant': 'clinic-south', 'bookings': 5},
]


class TestChargebackAggregation:
    def test_requires_billing_read(self):
        client = TestClient(_make_app(User({'id': 9, 'permissions': [],
                                            'admin': True})))
        resp = client.get('/ris/scheduling/chargeback')
        assert resp.status_code == 403

    def test_groups_by_requesting_site(self):
        client = TestClient(_make_app())
        conn = _Conn()
        conn.set_fetch(_ROWS)
        with patch('api.scheduling.get_conn', return_value=conn):
            resp = client.get('/ris/scheduling/chargeback'
                              '?month=2026-08-01')
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['data'][0]['requesting_tenant'] == 'clinic-north'
        assert body['data'][0]['bookings'] == 12
        call_args = conn.calls[0]
        sql = call_args[1]
        args = call_args[2]
        assert "requesting_tenant <> ''" in sql
        assert 'GROUP BY' in sql
        # month window passed as lower bound
        assert any(str(a).startswith('2026-08-01') for a in args)

    def test_month_defaults_to_current(self):
        from datetime import date
        client = TestClient(_make_app())
        conn = _Conn()
        conn.set_fetch([])
        with patch('api.scheduling.get_conn', return_value=conn):
            resp = client.get('/ris/scheduling/chargeback')
        assert resp.status_code == 200
        args = conn.calls[0][2]
        today = date.today().isoformat()
        assert any(str(a).startswith(today[:8]) for a in args)

    def test_invalid_month_422(self):
        client = TestClient(_make_app())
        with patch('api.scheduling.get_conn', return_value=_Conn()):
            resp = client.get('/ris/scheduling/chargeback?month=nope')
        assert resp.status_code == 422


class TestDashboardParityFields:
    """R2-06-05: chargeback rows + denial rate join the KPI payload."""

    def test_kpi_includes_chargeback_and_denial_rate(self):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)

        async def fetch(sql, *args):
            if 'ris_prior_auth_requests' in sql and 'GROUP BY' in sql:
                return [{'status': 'APPROVED', 'n': 5}]
            return []

        async def fetchval(sql, *args):
            if 'ris_claims' in sql:
                return 0.2
            if 'ris_prior_auth_requests' in sql:
                return 0.9
            if 'ris_appointments' in sql:
                return 0.5
            if 'worklist_entries' in sql:
                return 3
            return 0

        conn.fetch = fetch
        conn.fetchval = fetchval
        conn.fetchrow = AsyncMock(return_value={'total_unbilled': 4})

        # reuse the existing dashboard app helper
        import tests.test_ris_dashboard as dash_mod

        client = TestClient(dash_mod._make_dashboard_app(
            User({'id': 1, 'permissions': ['REPORT_READ']})))
        with patch('api.ris_dashboard.get_conn', return_value=conn):
            resp = client.get('/ris/dashboard/kpi')
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['chargeback']['month'] is not None
        assert isinstance(body['chargeback']['rows'], list)
        assert body['denial_rate'] == 0.2
