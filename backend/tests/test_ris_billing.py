"""Sprint S11 — RIS Billing Capture (E-RIS-11) tests.

Vertical-slice TDD per docs/RIS-integration/S4-S10_REMEDIATION_TDD_PIPELINE.md.
Covers: CPT/ICD-10 suggestions (S11-02/06), auto charge drop on sign-off
(S11-03), billing queue (S11-04), charge drop (S11-05), unbilled aging
(S11-07), 837/835 stubs (S11-09/10), and capture-rate reconciliation (S11-13).
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


def _make_billing_app(user=None):
    from api.billing import (
        RisCptSuggestionsHandler,
        RisBillingQueueHandler,
        RisChargeDropHandler,
        RisUnbilledHandler,
        RisClaimSubmitHandler,
        RisDenialImportHandler,
        RisReconciliationHandler,
    )

    return Starlette(
        routes=[
            Route('/ris/billing/cpt-suggestions',
                  endpoint=RisCptSuggestionsHandler),
            Route('/ris/billing/queue', endpoint=RisBillingQueueHandler),
            Route('/ris/billing/charges/{id}/drop',
                  endpoint=RisChargeDropHandler, methods=['POST']),
            Route('/ris/billing/unbilled', endpoint=RisUnbilledHandler),
            Route('/ris/billing/claims/{id}/submit',
                  endpoint=RisClaimSubmitHandler, methods=['POST']),
            Route('/ris/billing/denials/{id}/rework',
                  endpoint=RisDenialImportHandler, methods=['POST']),
            Route('/ris/billing/reconciliation',
                  endpoint=RisReconciliationHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user or User({'id': 1, 'permissions': []}))],
    )


def _user(*perms):
    return User({'id': 1, 'permissions': list(perms)})


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
# S11-02 / S11-06 — CPT/ICD-10 suggestion engine
# ---------------------------------------------------------------------------

class TestCodingService:
    """S11-02: procedure description -> CPT, indication -> ICD-10."""

    @pytest.mark.asyncio
    async def test_suggest_cpt_maps_procedure_to_code(self):
        from db.ris_coding import CodingService

        conn = _Conn()
        conn.set_fetch([{'procedure_code': 'CT CHEST', 'cpt_code': '71250',
                         'cpt_description': 'CT chest without contrast',
                         'icd10_code': 'R91.1', 'icd10_description': 'Lung opacity'}])
        service = CodingService(conn)
        got = await service.suggest_cpt('CT CHEST')
        assert got['cpt_code'] == '71250'
        assert got['cpt_description'] == 'CT chest without contrast'

    @pytest.mark.asyncio
    async def test_suggest_icd10_maps_indication(self):
        from db.ris_coding import CodingService

        conn = _Conn()
        conn.set_fetch([{'procedure_code': 'CT CHEST', 'cpt_code': '71250',
                         'icd10_code': 'R91.1', 'icd10_description': 'Lung opacity'}])
        service = CodingService(conn)
        got = await service.suggest_icd10('lung opacity')
        assert got['icd10_code'] == 'R91.1'

    @pytest.mark.asyncio
    async def test_unknown_procedure_returns_empty_suggestion(self):
        from db.ris_coding import CodingService

        conn = _Conn()
        conn.set_fetch([])
        service = CodingService(conn)
        got = await service.suggest_cpt('NOT A PROCEDURE')
        assert got == {}

    @pytest.mark.asyncio
    async def test_seed_defaults_inserts_coding_map_rows(self):
        from db.ris_coding import CodingService

        conn = _Conn()
        service = CodingService(conn)
        await service.seed_defaults()
        inserts = [sql for _m, sql, *_ in conn.calls if 'INSERT INTO ris_coding_map' in sql]
        assert inserts, 'seed_defaults must insert coding rows'
        # Idempotent: NOT EXISTS guard against duplicate procedure_code.
        assert 'WHERE NOT EXISTS' in inserts[0]


class TestCptSuggestionsApi:
    """S11-06: GET /ris/billing/cpt-suggestions — override works."""

    def test_requires_billing_read(self, conn):
        client = TestClient(_make_billing_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/cpt-suggestions?procedure=CT')
        assert resp.status_code == 403

    def test_returns_suggestions(self, conn):
        conn.set_fetch([{'procedure_code': 'CT CHEST', 'cpt_code': '71250',
                         'cpt_description': 'CT chest without contrast',
                         'icd10_code': 'R91.1', 'icd10_description': 'Lung opacity'}])
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/cpt-suggestions?procedure=CT CHEST')
        assert resp.status_code == 200
        body = resp.json()
        assert body['data'][0]['cpt_code'] == '71250'

    def test_empty_procedure_returns_validation_error(self, conn):
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/cpt-suggestions')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# S11-03 — auto charge drop on sign-off
# ---------------------------------------------------------------------------

class TestAutoChargeDrop:
    """S11-03: sign-off creates a full ris_charges row with coding."""

    @pytest.mark.asyncio
    async def test_drop_charge_creates_full_row(self, conn):
        from db.ris_charges import drop_charge

        conn.set_fetchrow({'id': 'chg-1'})
        await drop_charge(
            conn, report_id='rep-1', exam_id='exam-1',
            accession_number='ACC001', patient_id='P001',
            procedure_desc='CT CHEST', indication='lung opacity',
            radiologist_id='radio-1',
        )
        inserts = [(m, sql) for m, sql, *_ in conn.calls if 'INSERT INTO ris_charges' in sql]
        assert inserts, 'drop_charge must insert a ris_charges row'
        sql = inserts[0][1]
        assert 'cpt_code' in sql
        assert 'icd10_code' in sql
        assert 'charge_amount' in sql
        assert 'status' in sql

    @pytest.mark.asyncio
    async def test_drop_charge_is_idempotent(self, conn):
        from db.ris_charges import drop_charge

        conn.set_fetchrow({'id': 'chg-1'})
        await drop_charge(
            conn, report_id='rep-1', exam_id='exam-1',
            accession_number='ACC001', patient_id='P001',
            procedure_desc='CT CHEST', indication='lung opacity',
            radiologist_id='radio-1',
        )
        await drop_charge(
            conn, report_id='rep-1', exam_id='exam-1',
            accession_number='ACC001', patient_id='P001',
            procedure_desc='CT CHEST', indication='lung opacity',
            radiologist_id='radio-1',
        )
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_charges' in sql]
        assert len(inserts) == 2, 'both calls must execute the guarded INSERT'
        for sql in inserts:
            assert 'WHERE NOT EXISTS' in sql


# ---------------------------------------------------------------------------
# S11-04 — billing queue API
# ---------------------------------------------------------------------------

class TestBillingQueueApi:
    """S11-04: GET /ris/billing/queue — signed-but-unbilled charges."""

    def test_requires_billing_read(self, conn):
        client = TestClient(_make_billing_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/queue')
        assert resp.status_code == 403

    def test_returns_pending_charges(self, conn):
        conn.set_fetch([{'id': 'chg-1', 'patient_id': 'P001',
                         'patient_name': 'Smith^John', 'accession_number': 'ACC001',
                         'cpt_code': '71250', 'cpt_description': 'CT chest',
                         'icd10_code': 'R91.1', 'charge_amount': 250.0,
                         'status': 'PENDING'}])
        conn.set_fetchval(1)
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/queue')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total'] == 1
        assert body['data'][0]['cpt_code'] == '71250'


# ---------------------------------------------------------------------------
# S11-05 — charge drop API
# ---------------------------------------------------------------------------

class TestChargeDropApi:
    """S11-05: POST /ris/billing/charges/{id}/drop -> BILLED + audit."""

    def test_requires_billing_write(self, conn):
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/charges/chg-1/drop')
        assert resp.status_code == 403

    def test_drop_marks_billed(self, conn):
        conn.set_fetchrow({'id': 'chg-1', 'status': 'PENDING'})
        client = TestClient(_make_billing_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/charges/chg-1/drop')
        assert resp.status_code == 200
        updates = [sql for _m, sql, *_ in conn.calls if 'UPDATE ris_charges' in sql]
        assert updates, 'charge drop must UPDATE ris_charges'
        assert "status = 'BILLED'" in updates[0]

    def test_missing_charge_returns_404(self, conn):
        conn.set_fetchrow(None)
        client = TestClient(_make_billing_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/charges/missing/drop')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# S11-07 — unbilled aging API
# ---------------------------------------------------------------------------

class TestUnbilledAgingApi:
    """S11-07: GET /ris/billing/unbilled — $0 > 5 days grouped."""

    def test_requires_billing_read(self, conn):
        client = TestClient(_make_billing_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/unbilled')
        assert resp.status_code == 403

    def test_returns_aging_groups(self, conn):
        conn.set_fetch([
            {'date': '2026-08-10', 'facility_name': 'Main', 'payer_name': 'Medicare',
             'count': 2, 'total_amount': 500.0, 'oldest_charge_days': 11},
        ])
        conn.set_fetchval(2)
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/unbilled')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total_unbilled'] == 2
        assert body['groups'][0]['oldest_charge_days'] == 11


# ---------------------------------------------------------------------------
# S11-09 / S11-10 — 837 export + 835 import stubs
# ---------------------------------------------------------------------------

class TestClaimStubs:
    """S11-09: submit claim -> ris_claims row. S11-10: denial rework."""

    def test_submit_claim_creates_claim(self, conn):
        conn.set_fetchrow({'id': 'chg-1', 'status': 'PENDING', 'patient_id': 'P001'})
        conn.set_fetchval('clm-1')
        client = TestClient(_make_billing_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/claims/chg-1/submit')
        assert resp.status_code == 200
        inserts = [sql for _m, sql, *_ in conn.calls if 'INSERT INTO ris_claims' in sql]
        assert inserts, 'submit must insert a ris_claims row'

    def test_denial_rework_records_denial(self, conn):
        conn.set_fetchrow({'id': 'clm-1', 'status': 'DRAFT'})
        client = TestClient(_make_billing_app(_user(Permission.BILLING_WRITE)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/denials/clm-1/rework')
        assert resp.status_code == 200
        updates = [sql for _m, sql, *_ in conn.calls if 'UPDATE ris_claims' in sql]
        assert updates, 'rework must UPDATE ris_claims'
        assert "'DENIED'" in updates[0]


# ---------------------------------------------------------------------------
# S11-13 — capture-rate reconciliation
# ---------------------------------------------------------------------------

class TestReconciliationApi:
    """S11-13: signed reports vs charged reports — capture rate."""

    def test_requires_billing_read(self, conn):
        client = TestClient(_make_billing_app(_user()))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/reconciliation')
        assert resp.status_code == 403

    def test_returns_capture_rate(self, conn):
        # 10 signed, 8 charged -> 80%.
        conn.set_fetchval(10)
        # fetchval is called twice: signed then charged.
        async def _fetchval(sql, *args):
            if 'FROM reports' in sql:
                return 10
            return 8
        conn.fetchval = _fetchval
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/reconciliation')
        assert resp.status_code == 200
        body = resp.json()
        assert body['signed_reports'] == 10
        assert body['charged_reports'] == 8
        assert body['capture_rate_pct'] == 80.0

    def test_zero_signed_reports_is_full_capture(self, conn):
        conn.set_fetchval(0)
        client = TestClient(_make_billing_app(_user(Permission.BILLING_READ)))
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/reconciliation')
        assert resp.status_code == 200
        assert resp.json()['capture_rate_pct'] == 100.0

class TestChargeDropRealDb:
    """A1 (GAP_AUDIT_TDD_PIPELINE.md): the S8-14 stub must not shadow the
    enriched S11-03 charge drop.

    Regression net for the C-1 finding: Reports.sign() used to fire
    drop_charge_stub first, and the per-report NOT EXISTS guard then made
    the enriched drop_charge() a silent no-op — bare $0 charges with no
    coding, wrong tenant. Repo-level sign() creates NO charges; the API
    sign handler is the single writer of one ENRICHED row.

    Runs against the real database via an in-loop ASGI transport (same
    pattern as tests/test_tracking_status_constraint.py) so cross-module
    side effects are exercised end-to-end."""

    @pytest.fixture(autouse=True)
    async def setup_db(self):
        from db.conn import database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.close()

    async def _seed_exam_and_report(self, conn, tag):
        from db.reports import Reports
        exam_row = await conn.fetchrow(
            "INSERT INTO exams (accession_number, patient_id, patient_name,"
            " status, modality, requested_procedure_desc)"
            " VALUES ($1, $2, $3, 'completed', 'CT', 'CT head')"
            " RETURNING id",
            f'ACC-A1-{tag}', f'PAT-A1-{tag}', 'A1 RealDb Patient',
        )
        report = await Reports(conn).create(
            exam_row['id'],
            {'status': 'draft',
             'findings': 'CT head clear',
             'impression': 'No acute findings'},
            created_by='rad-9',
        )
        return exam_row, report

    @pytest.mark.asyncio
    async def test_repo_sign_does_not_create_any_charge(self):
        import uuid
        from db.conn import get_conn
        from db.reports import Reports

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            _exam, report = await self._seed_exam_and_report(conn, tag)
            try:
                signed = await Reports(conn).sign(
                    report['id'], signed_by='rad-9')
                assert signed['status'] == 'final'

                count = await conn.fetchval(
                    'SELECT count(*) FROM ris_charges WHERE report_id = $1',
                    str(report['id']),
                )
                assert count == 0, (
                    'Reports.sign() is a pure status transition + version '
                    'snapshot; charge creation belongs to the API sign '
                    'handler (single enriched writer) — found %d stub '
                    'row(s)' % count
                )
            finally:
                await conn.execute(
                    'DELETE FROM ris_charges WHERE report_id = $1',
                    str(report['id']),
                )

    @pytest.mark.asyncio
    async def test_api_sign_drops_exactly_one_enriched_charge(self):
        import uuid
        import httpx
        from db.conn import get_conn
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.routing import Route
        from api.reports import ExamReportSignHandler

        tag = uuid.uuid4().hex[:6]
        user = User({'id': 'rad-9', 'permissions': ['REPORT_SIGN'],
                     'tenant': 'default'})
        app = Starlette(
            routes=[Route('/reports/{exam_id}/sign',
                          endpoint=ExamReportSignHandler)],
            middleware=[Middleware(_FakeAuth, user=user)],
        )

        async with get_conn() as conn:
            exam_row, report = await self._seed_exam_and_report(conn, tag)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                    transport=transport, base_url='http://test') as client:
                resp = await client.post(
                    f'/reports/{exam_row["id"]}/sign',
                    json={'confirm': True},
                )
            assert resp.status_code == 200, resp.text

            async with get_conn() as conn:
                rows = await conn.fetch(
                    'SELECT * FROM ris_charges WHERE report_id = $1',
                    str(report['id']),
                )
                assert len(rows) == 1, (
                    'exactly one charge per signed report, found %d'
                    % len(rows)
                )
                charge = rows[0]
                assert charge['cpt_code'] == '70450', (
                    'charge must carry the CodingService CPT suggestion, '
                    'got %r' % charge['cpt_code']
                )
                assert charge['icd10_code'] == 'R51'
                assert charge['patient_name'] == 'A1 RealDb Patient'
                assert charge['tenant_id'] == 'default'
        finally:
            async with get_conn() as conn:
                await conn.execute(
                    'DELETE FROM ris_charges WHERE report_id = $1',
                    str(report['id']),
                )
