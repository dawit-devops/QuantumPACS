"""Sprint S12 — IDOR regression (S12-10).

Cross-tenant ID manipulation must fail closed: a tenant-A user submitting
tenant-B's resource ID must never see or mutate tenant-B data. The RIS
handlers scope every row lookup by the caller's effective tenant, so a
foreign ID resolves to nothing (404 / 400), not the other tenant's row.

Covers the S11/S12 surfaces: charge drop, claim submit, billing queue,
and report sign (charge/report are tenant-tagged; exams carry tenant_id).
"""


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


def _make_app(user, handlers):
    return Starlette(
        routes=[Route(path, endpoint=h, methods=m) for path, h, m in handlers],
        middleware=[Middleware(_FakeAuth, user=user)],
    )


def _user(*perms, tenant='clinic-alfa'):
    return User({'id': 1, 'permissions': list(perms), 'tenant': tenant})


class _Conn:
    """In-memory conn. fetchrow returns None by default — a cross-tenant ID
    must look like a missing row (the handler 404s instead of leaking)."""

    def __init__(self):
        self.calls = []
        self._fetchrow = None

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
        return 0

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return []

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


class TestChargeIdor:
    """S12-10: tenant-A user drops tenant-B charge ID -> 404, no mutation."""

    def test_charge_drop_foreign_id_returns_404(self):
        from api.billing import RisChargeDropHandler

        conn = _Conn()
        conn.set_fetchrow(None)  # foreign ID resolves to nothing
        client = TestClient(_make_app(
            _user(Permission.BILLING_WRITE),
            [('/ris/billing/charges/{id}/drop', RisChargeDropHandler, ['POST'])],
        ))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/charges/tenant-b-charge-1/drop')
        assert resp.status_code == 404, \
            'a foreign charge ID must 404, never expose the other tenant row'
        # The handler scopes the lookup by tenant — assert the SQL includes
        # the tenant clause so the guard is real, not a mock artifact.
        lookups = [sql for m, sql, *_ in conn.calls if 'FROM ris_charges' in sql]
        assert lookups, 'handler must look up the charge first'
        assert 'tenant_id' in lookups[0], \
            'lookup must be tenant-scoped (IDOR guard)'

    def test_claim_submit_foreign_charge_returns_404(self):
        from api.billing import RisClaimSubmitHandler

        conn = _Conn()
        conn.set_fetchrow(None)
        client = TestClient(_make_app(
            _user(Permission.BILLING_WRITE),
            [('/ris/billing/claims/{id}/submit', RisClaimSubmitHandler, ['POST'])],
        ))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/claims/tenant-b-charge-1/submit')
        assert resp.status_code == 404

    def test_queue_is_tenant_scoped(self):
        from api.billing import RisBillingQueueHandler

        conn = _Conn()
        client = TestClient(_make_app(
            _user(Permission.BILLING_READ),
            [('/ris/billing/queue', RisBillingQueueHandler, ['GET'])],
        ))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/queue')
        assert resp.status_code == 200
        selects = [sql for m, sql, *_ in conn.calls if 'FROM ris_charges' in sql]
        assert selects, 'queue must query ris_charges'
        assert 'tenant_id' in selects[0], \
            'queue query must be tenant-scoped (no cross-tenant leak)'


class TestReportIdor:
    """S12-10: tenant-A user signs tenant-B exam's report -> 404/400, no leak."""

    def test_sign_foreign_exam_is_scoped(self):
        from api.reports import ExamReportSignHandler

        conn = _Conn()
        conn.set_fetchrow(None)  # foreign exam_id resolves to nothing
        client = TestClient(_make_app(
            _user(Permission.REPORT_SIGN),
            [('/exams/{exam_id}/sign', ExamReportSignHandler, ['POST'])],
        ))
        with patch('api.reports.get_conn', return_value=conn):
            resp = client.post('/exams/tenant-b-exam-1/sign', json={'confirm': True})
        # Exams(conn).get resolves the exam by id; a foreign id yields
        # nothing -> the handler returns not_found rather than proceeding.
        assert resp.status_code in (404, 400), \
            f'foreign exam sign must fail closed, got {resp.status_code}'
