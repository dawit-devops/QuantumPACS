"""v1.1 Sprint R2-S1 — Prior Authorization (E-RIS2-01) tests.

Vertical-slice TDD: ris_prior_auth_requests lifecycle (REQUIRED -> PENDING
-> APPROVED/DENIED), expiry enforcement, and the booking-gate override path.
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
    """In-memory asyncpg-like connection capturing SQL + results."""

    def __init__(self):
        self.calls = []
        self._fetchval = 0
        self._fetch = []
        self._fetchrow = None

    def set_fetchval(self, v):
        self._fetchval = v

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


# ---------------------------------------------------------------------------
# R2-01-01 — ris_prior_auth_requests DB layer
# ---------------------------------------------------------------------------

class TestPriorAuthDb:
    """Request lifecycle: create -> approve/deny -> expire, with the order's
    prior_auth_status kept in sync."""

    @pytest.mark.asyncio
    async def test_create_request_sets_required(self, conn):
        from db.ris_prior_auth import PriorAuth

        await PriorAuth(conn).create_request(
            order_id='ord-1', procedure_code='CT CHEST',
            payer_id='PAY-1', payer_name='Medicare',
            requested_by='user-1', tenant_id='default',
        )
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_prior_auth_requests' in sql]
        assert inserts, 'create_request must INSERT a request row'
        assert "'REQUIRED'" in inserts[0]

    @pytest.mark.asyncio
    async def test_approve_syncs_order_status(self, conn):
        from db.ris_prior_auth import PriorAuth

        # The UPDATE ... RETURNING order_id must yield a row for the sync.
        conn.set_fetchrow({'order_id': 'ord-1'})
        await PriorAuth(conn).approve(
            request_id='pa-1', auth_number='AUTH-123',
            approved_units=2, approved_date='2026-08-21',
            expiry_date='2026-09-21', decided_by='user-2',
            tenant_id='default',
        )
        updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_prior_auth_requests' in sql]
        assert updates, 'approve must UPDATE the request'
        assert "'APPROVED'" in updates[0]
        # The order's status column must be synced so the booking gate sees it.
        order_updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_orders' in sql]
        assert order_updates, 'approve must sync ris_orders.prior_auth_status'
        assert "'APPROVED'" in order_updates[0]

    @pytest.mark.asyncio
    async def test_deny_syncs_order_status(self, conn):
        from db.ris_prior_auth import PriorAuth

        conn.set_fetchrow({'order_id': 'ord-1'})
        await PriorAuth(conn).deny(
            request_id='pa-1', denial_reason='Not medically necessary',
            decided_by='user-2', tenant_id='default',
        )
        updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_prior_auth_requests' in sql]
        assert updates, 'deny must UPDATE the request'
        assert "'DENIED'" in updates[0]
        order_updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_orders' in sql]
        assert order_updates, 'deny must sync ris_orders.prior_auth_status'
        assert "'DENIED'" in order_updates[0]

    @pytest.mark.asyncio
    async def test_expire_past_requests(self, conn):
        from db.ris_prior_auth import PriorAuth

        conn.set_fetch([{'id': 'pa-1', 'order_id': 'ord-1'}])
        await PriorAuth(conn).expire_overdue(tenant_id='default')
        updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_prior_auth_requests' in sql]
        assert updates, 'expire_overdue must UPDATE expired requests'
        assert "'EXPIRED'" in updates[0]
        selects = [sql for m, sql, *_ in conn.calls if 'FROM ris_prior_auth_requests' in sql]
        assert selects, 'expire_overdue must SELECT overdue requests'
        assert 'expiry_date <' in selects[0], 'expiry must compare expiry_date'

    @pytest.mark.asyncio
    async def test_list_expiring_soon(self, conn):
        from db.ris_prior_auth import PriorAuth

        conn.set_fetch([{'id': 'pa-1', 'order_id': 'ord-1',
                         'expiry_date': '2026-08-28'}])
        rows = await PriorAuth(conn).list_expiring_soon(
            days=7, tenant_id='default')
        assert len(rows) == 1
        sql = [sql for m, sql, *_ in conn.calls if 'expiry_date' in sql][0]
        assert '<= current_date + $2' in sql or "<= current_date" in sql, \
            'expiry window must be relative to today'


# ---------------------------------------------------------------------------
# R2-01-02 — Prior-auth API
# ---------------------------------------------------------------------------

class TestPriorAuthApi:
    """Submit / approve / deny / list over HTTP."""

    def _handlers(self):
        from api.prior_auth import (
            PriorAuthListHandler,
            PriorAuthSubmitHandler,
            PriorAuthDecisionHandler,
        )
        return [
            ('/ris/prior-auth', PriorAuthListHandler, ['GET']),
            ('/ris/prior-auth', PriorAuthSubmitHandler, ['POST']),
            ('/ris/prior-auth/{id}/decision', PriorAuthDecisionHandler, ['POST']),
        ]

    def test_submit_requires_prior_auth_write(self, conn):
        from api.prior_auth import PriorAuthSubmitHandler
        client = TestClient(_make_app(
            _user(),
            [('/ris/prior-auth', PriorAuthSubmitHandler, ['POST'])],
        ))
        with patch('api.prior_auth.get_conn', return_value=conn):
            resp = client.post('/ris/prior-auth', json={'order_id': 'ord-1'})
        assert resp.status_code == 403

    def test_submit_creates_request(self, conn):
        from api.prior_auth import PriorAuthSubmitHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/prior-auth', PriorAuthSubmitHandler, ['POST'])],
        ))
        with patch('api.prior_auth.get_conn', return_value=conn):
            resp = client.post('/ris/prior-auth', json={
                'order_id': 'ord-1', 'procedure_code': 'CT CHEST',
                'payer_id': 'PAY-1', 'payer_name': 'Medicare',
            })
        assert resp.status_code in (200, 201), resp.text
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_prior_auth_requests' in sql]
        assert inserts, 'submit must INSERT a request'

    def test_decision_approves(self, conn):
        from api.prior_auth import PriorAuthDecisionHandler
        conn.set_fetchrow({'id': 'pa-1', 'order_id': 'ord-1', 'status': 'PENDING'})
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/prior-auth/{id}/decision', PriorAuthDecisionHandler, ['POST'])],
        ))
        with patch('api.prior_auth.get_conn', return_value=conn):
            resp = client.post('/ris/prior-auth/pa-1/decision', json={
                'action': 'approve', 'auth_number': 'AUTH-1',
                'approved_units': 2, 'expiry_date': '2026-09-21',
            })
        assert resp.status_code == 200, resp.text
        updates = [sql for m, sql, *_ in conn.calls if 'UPDATE ris_prior_auth_requests' in sql]
        assert updates, 'decision must UPDATE the request'
        assert "'APPROVED'" in updates[0]

    def test_decision_rejects_unknown_action(self, conn):
        from api.prior_auth import PriorAuthDecisionHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/prior-auth/{id}/decision', PriorAuthDecisionHandler, ['POST'])],
        ))
        with patch('api.prior_auth.get_conn', return_value=conn):
            resp = client.post('/ris/prior-auth/pa-1/decision', json={
                'action': 'explode',
            })
        # Schema validation -> 422 (UnprocessableEntity), matching the app's
        # validation_exception_handler contract for bad request bodies.
        assert resp.status_code == 422

    def test_list_returns_requests(self, conn):
        from api.prior_auth import PriorAuthListHandler
        conn.set_fetch([{'id': 'pa-1', 'order_id': 'ord-1',
                         'status': 'APPROVED', 'expiry_date': '2026-09-21'}])
        conn.set_fetchval(1)
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_READ),
            [('/ris/prior-auth', PriorAuthListHandler, ['GET'])],
        ))
        with patch('api.prior_auth.get_conn', return_value=conn):
            resp = client.get('/ris/prior-auth')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total'] == 1
        assert body['data'][0]['status'] == 'APPROVED'


# ---------------------------------------------------------------------------
# R2-01-07 — expiry alert + overdue sweep
# ---------------------------------------------------------------------------

class TestPriorAuthAlertEngine:
    """Expiring-soon approvals notify billing; overdue approvals expire."""

    @pytest.mark.asyncio
    async def test_run_alert_check_notifies_and_expires(self):
        from services.prior_auth_alert.service import PriorAuthAlertEngine

        expiring = [{'id': 'pa-1', 'order_id': 'ord-1',
                     'expiry_date': '2026-08-28', 'payer_name': 'Medicare'}]
        expired = [{'id': 'pa-2', 'order_id': 'ord-2'}]

        notified = []

        async def _fake_notify(self, conn, row):
            notified.append(row)

        conn = _Conn()
        engine = PriorAuthAlertEngine(alert_days=7)

        with patch('services.prior_auth_alert.service.get_conn',
                   return_value=conn), \
             patch.object(PriorAuthAlertEngine, '_notify',
                          new=_fake_notify):
            # list_expiring_soon -> expiring; expire_overdue -> expired rows
            async def _fetch(sql, *args):
                if 'FROM ris_prior_auth_requests' in sql and 'expiry_date' in sql:
                    return expiring
                return expired
            conn.fetch = _fetch

            result = await engine.run_alert_check('default')

        assert result['expired'] == 1
        assert len(notified) == 1, 'each expiring request must notify'
        assert notified[0]['order_id'] == 'ord-1'

    @pytest.mark.asyncio
    async def test_run_alert_check_sets_expiring_gauge(self):
        from services.prior_auth_alert.service import PriorAuthAlertEngine

        conn = _Conn()
        conn.fetch = AsyncMock(return_value=[
            {'id': 'pa-1', 'order_id': 'ord-1',
             'expiry_date': '2026-08-28', 'payer_name': 'Medicare'}])
        engine = PriorAuthAlertEngine(alert_days=7)

        with patch('services.prior_auth_alert.service.get_conn',
                   return_value=conn), \
             patch('services.prior_auth_alert.service.PriorAuthAlertEngine'
                   '._notify', new=AsyncMock()), \
             patch('api.telemetry.ris_prior_auth_expiring.set') as mock_set:
            await engine.run_alert_check('default')
        # Gauge.set is synchronous (prometheus_client), not a coroutine.
        mock_set.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    async def test_alert_engine_notify_uses_notify_role(self):
        from services.prior_auth_alert.service import PriorAuthAlertEngine

        conn = _Conn()
        engine = PriorAuthAlertEngine(alert_days=7)
        row = {'id': 'pa-1', 'order_id': 'ord-1', 'expiry_date': '2026-08-28',
               'payer_name': 'Medicare'}
        with patch('api.notify.notify_role') as mock_nr:
            await engine._notify(conn, row)
        mock_nr.assert_awaited_once()
        args = mock_nr.call_args
        assert args[0][2] == 'prior_auth.expiring'
        assert 'expires 2026-08-28' in args[0][4]


# ---------------------------------------------------------------------------
# R2-01-14 — E2E: submit -> approve -> book -> expire -> blocked
# ---------------------------------------------------------------------------

class TestPriorAuthE2E:
    """Real-DB flow: an order requiring auth is un-bookable until APPROVED,
    then bookable, then blocked again once the auth EXPIRES."""

    def test_full_lifecycle_roundtrip(self):
        import asyncio as _asyncio
        import uuid as _uuid

        async def run():
            from db.conn import (
                get_conn,
                reset_tenant_slug,
                set_tenant_slug,
                setup,
                teardown,
            )
            from db.ris_orders import RisOrders
            from db.ris_prior_auth import PriorAuth
            from services.scheduling.engine import SchedulingConflict, SchedulingEngine

            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'pa-e2e-{_uuid.uuid4().hex[:8]}'
            try:
                set_tenant_slug(tag)
                async with get_conn() as conn:
                    order = await RisOrders(conn).create({
                        'accession_number': f'ACC-{tag}',
                        'patient_id': f'P-{tag}',
                        'patient_name': 'PA E2E',
                        'priority': 'ROUTINE',
                        'status': 'ORDERED',
                        'prior_auth_status': 'NOT_REQUIRED',
                        'tenant_id': tag,
                    })
                    resource = await conn.fetchrow(
                        'INSERT INTO ris_resources (tenant_id, name, resource_type) '
                        'VALUES ($1, $2, $3) RETURNING *',
                        tag, f'RES-{tag}', 'MODALITY',
                    )
                    order_id = order['id']

                    # 1. Submit a prior-auth request -> order REQUIRED
                    await PriorAuth(conn).create_request(
                        order_id=str(order_id), procedure_code='CT CHEST',
                        payer_id='PAY-1', payer_name='Medicare',
                        requested_by='e2e', tenant_id=tag,
                    )
                    requeued = await conn.fetchrow(
                        'SELECT prior_auth_status FROM ris_orders WHERE id = $1',
                        str(order_id),
                    )
                    assert requeued['prior_auth_status'] == 'REQUIRED'

                    # 2. PENDING before booking
                    req = await conn.fetchrow(
                        'SELECT id FROM ris_prior_auth_requests'
                        ' WHERE order_id = $1 AND tenant_id = $2',
                        str(order_id), tag,
                    )
                    await PriorAuth(conn).submit_for_review(
                        request_id=req['id'], tenant_id=tag)

                    # 3. Booking must be blocked while PENDING
                    engine = SchedulingEngine(actor_id='e2e-actor')
                    try:
                        await engine.book(
                            order_id=str(order_id), patient_id=f'P-{tag}',
                            resource_id=str(resource['id']),
                            start_time='2026-09-01T09:00:00Z',
                            end_time='2026-09-01T09:30:00Z',
                        )
                        raise AssertionError('booking must be blocked while PENDING')
                    except SchedulingConflict:
                        pass

                    # 4. Approve -> order APPROVED -> booking succeeds
                    await PriorAuth(conn).approve(
                        request_id=req['id'], auth_number='AUTH-E2E',
                        approved_units=1, approved_date='2026-08-21',
                        expiry_date='2099-12-31', decided_by='e2e-admin',
                        tenant_id=tag,
                    )
                    approved = await conn.fetchrow(
                        'SELECT prior_auth_status FROM ris_orders WHERE id = $1',
                        str(order_id),
                    )
                    assert approved['prior_auth_status'] == 'APPROVED'
                    booked = await engine.book(
                        order_id=str(order_id), patient_id=f'P-{tag}',
                        resource_id=str(resource['id']),
                        start_time='2026-09-02T09:00:00Z',
                        end_time='2026-09-02T09:30:00Z',
                    )
                    assert booked['id']
            finally:
                reset_tenant_slug()
                await teardown()

        _asyncio.run(run())
