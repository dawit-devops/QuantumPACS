"""R2-03-05/08 — IDN multi-site scheduling.

Grant-holding schedulers (teleradiology/IDN) search availability ACROSS
their accessible facilities in one call; bookings themselves stay
home-facility (TenantMiddleware write scopes) and every appointment now
records the requesting site for chargeback.
"""

import pytest

from datetime import date
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


def _user(home='clinic-a', *perms):
    return User({'id': 9, 'tenant': home,
                 'permissions': list(perms or ['SCHEDULE_READ'])})


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
        return self._fetchrow


def _make_app(user=None):
    from api.scheduling import MultiSiteAvailabilityHandler

    return Starlette(
        routes=[Route('/ris/scheduling/multisite-availability',
                      endpoint=MultiSiteAvailabilityHandler)],
        middleware=[Middleware(_FakeAuth,
                               user=user or _user())],
    )


class TestMultiSiteAvailability:
    def test_requires_schedule_read(self):
        client = TestClient(_make_app(User({'id': 9, 'tenant': 'a',
                                            'permissions': []})))
        resp = client.get(
            '/ris/scheduling/multisite-availability?date=2026-08-25')
        assert resp.status_code == 403

    def test_fans_out_across_home_and_granted_sites(self):
        client = TestClient(_make_app())
        conn = _Conn()
        # list_for_user -> granted slugs; per-site resources fetch.
        granted = [{'tenant_slug': 'clinic-b'}, {'tenant_slug': 'clinic-c'}]
        resources = [
            {'id': 'r1', 'name': 'CT 1', 'resource_type': 'MODALITY'},
        ]
        with patch('api.scheduling.get_conn', return_value=conn), \
             patch('db.user_tenant_grants.UserTenantGrants.list_for_user',
                   AsyncMock(return_value=granted)), \
             patch('db.tenants.Tenants') as MockTenants, \
             patch('api.scheduling.RisResources') as MockRes, \
             patch('dcm.store.tenant_db_scope') as scope:
            instance = MockTenants.return_value
            instance.get_by_slug = AsyncMock(side_effect=lambda slug: (
                {'slug': slug, 'name': slug.upper()}
                if slug != 'clinic-c' else None))
            MockRes.return_value.list_for_tenant = AsyncMock(return_value=resources)
            scope.return_value.__aenter__ = AsyncMock(return_value=None)
            scope.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.get(
                '/ris/scheduling/multisite-availability?date=2026-08-25')
        assert resp.status_code == 200, resp.text
        sites = resp.json()['data']['sites']
        slugs = [s['site'] for s in sites]
        assert 'clinic-a' in slugs, 'home site always included'
        assert 'clinic-b' in slugs, 'granted site included'
        assert 'clinic-c' not in slugs, 'unregistered grant skipped'

    def test_date_required(self):
        client = TestClient(_make_app())
        resp = client.get('/ris/scheduling/multisite-availability')
        assert resp.status_code == 422


class TestChargebackTag:
    @pytest.mark.asyncio
    async def test_booking_stamps_requesting_site(self):
        """R2-03-08: the appointment records the requester's home tenant."""
        from db.ris_appointments import RisAppointments

        updates = []

        class _Conn2:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def execute(self, sql, *args):
                updates.append((sql, args))

        with patch('api.scheduling.SchedulingEngine') as MockEngine:
            MockEngine.return_value.book = AsyncMock(
                return_value={'id': 'appt-1', 'status': 'BOOKED'})
            from api.scheduling import RisAppointmentsHandler
            handler = object.__new__(RisAppointmentsHandler)

            body = type('B', (), {
                'order_id': 'o1', 'patient_id': 'p1',
                'resource_id': 'r1',
                'start_time': '2026-08-25T09:00:00+00:00',
                'end_time': '2026-08-25T09:30:00+00:00',
                'reason': '', 'override_reason': '',
            })()
            request = type('R', (), {
                'path_params': {},
                'user': User({'id': 5, 'tenant': 'clinic-x',
                              'permissions': ['SCHEDULE_WRITE']}),
                'json': AsyncMock(return_value={}),
            })()
            conn = _Conn2()

            with patch('api.scheduling.parse_body',
                       AsyncMock(return_value=body)), \
                 patch('api.scheduling.get_conn',
                       return_value=conn), \
                 patch('api.scheduling.created',
                       lambda d: d) as created_mock:
                await RisAppointmentsHandler.post(handler, request)
        assert updates, 'booking must stamp the requesting site'
        sql, args = updates[0]
        assert 'requesting_tenant' in sql
        assert 'clinic-x' in [str(a) for a in args]


class TestPerSiteSlaLabels:
    def test_mpps_histogram_has_facility_label(self):
        from api.telemetry import ris_mpps_latency_seconds
        labels = list(ris_mpps_latency_seconds._labelnames or [])
        assert 'facility' in labels, (
            'per-site SLA requires a facility label (R2-03-09)')
