"""R2-S3/S4 — denial rework chain (R2-02-01..04) + auth linkage (R2-01-08).

The S11-10 intake stub recorded a fixed DEN-001 code and offered no path
back to SUBMITTED. This suite drives the real chain:

    835-style payload -> parse -> rework queue -> correction + resubmit
    (full history) -> prior-auth number carried on the claim line.
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
    from api.billing import (
        RisDenialQueueHandler,
        RisDenialImportHandler,
        RisClaimResubmitHandler,
        RisClaimHistoryHandler,
    )

    return Starlette(
        routes=[
            Route('/ris/billing/denials', endpoint=RisDenialQueueHandler),
            Route('/ris/billing/denials/import',
                  endpoint=RisDenialImportHandler, methods=['POST']),
            Route('/ris/billing/claims/{id}/resubmit',
                  endpoint=RisClaimResubmitHandler, methods=['POST']),
            Route('/ris/billing/claims/{id}/history',
                  endpoint=RisClaimHistoryHandler),
        ],
        middleware=[Middleware(_FakeAuth,
                               user=user or User({'id': 1, 'permissions': []}))],
    )


def _user(*perms):
    return User({'id': 9, 'permissions': list(perms)})


class _Conn:
    def __init__(self):
        self.calls = []
        self._fetchval = 0
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

    async def fetchval(self, sql, *args):
        return self._fetchval

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


# ---------------------------------------------------------------------------
# Denial parsing (R2-02-01)
# ---------------------------------------------------------------------------

class TestDenialParse:
    def test_known_carc_code_passes_through(self):
        from db.ris_charges import parse_denial
        parsed = parse_denial({
            'claim_adjustment_reason_code': 'CO-16',
            'reason_text': 'Missing information',
        })
        assert parsed['code'] == 'CO-16'
        assert 'Missing information' in parsed['reason']

    def test_unknown_code_maps_to_other(self):
        from db.ris_charges import parse_denial
        parsed = parse_denial({'foo': 'bar'})
        assert parsed['code'] == 'OTHER'
        assert parsed['reason'], 'raw payload preserved in reason'

    def test_accepts_flat_keys(self):
        from db.ris_charges import parse_denial
        parsed = parse_denial({'code': 'PR-204', 'reason': 'Not covered'})
        assert parsed == {'code': 'PR-204', 'reason': 'Not covered'}


# ---------------------------------------------------------------------------
# DB layer: correction + resubmission with history (R2-02-03)
# ---------------------------------------------------------------------------

class TestReworkDb:
    @pytest.mark.asyncio
    async def test_correct_and_resubmit_bumps_and_logs(self):
        from db.ris_charges import RisClaims

        conn = _Conn()
        conn.set_fetchrow({'id': 'clm-1', 'status': 'SUBMITTED'})
        claims = RisClaims(conn)
        with patch.object(claims, 'fetchone',
                          AsyncMock(return_value={'id': 'clm-1',
                                                  'status': 'SUBMITTED'})):
            row = await claims.correct_and_resubmit(
                'clm-1', note='fixed CPT', actor='coder-1',
                tenant_id='default')
        assert row['status'] == 'SUBMITTED'
        writes = [c for c in conn.calls if 'UPDATE ris_claims' in c[1]
                  or 'INSERT INTO ris_claim_events' in c[1]]
        assert any('INSERT INTO ris_claim_events' in c[1] for c in writes), \
            'correction must append a claim event'
        updates = [c for c in writes if 'UPDATE ris_claims' in c[1]]
        assert updates, 'resubmit must update the claim'
        update_sql = updates[0][1]
        assert 'correction_count' in update_sql
        assert 'resubmitted_at' in update_sql
        # Event insert carries actor + note + tenant params.
        inserts = [c for c in writes if 'INSERT INTO ris_claim_events' in c[1]]
        assert 'coder-1' in [str(a) for a in inserts[0][2]]

    @pytest.mark.asyncio
    async def test_history_returns_events_for_claim(self):
        from db.ris_charges import RisClaims

        conn = _Conn()
        events = [{'event_type': 'DENIED'}, {'event_type': 'CORRECTION'}]
        conn.set_fetch(events)
        with patch.object(RisClaims(conn), 'fetch',
                          AsyncMock(return_value=events)):
            rows = await RisClaims(conn).get_history('clm-1', 'default')
        assert rows == events


# ---------------------------------------------------------------------------
# API surface (R2-02-01..04)
# ---------------------------------------------------------------------------

_DENIED_ROW = {
    'id': 'clm-9', 'tenant_id': 'default', 'status': 'DENIED',
    'claim_number': 'CLM-123456', 'payer_name': 'Medicare',
    'rejection_code': 'CO-16', 'rejection_reason': 'Missing information',
    'correction_count': 0, 'prior_auth_number': 'AUTH-77',
    'patient_name': 'Jane Doe', 'accession_number': 'ACC-1',
    'cpt_code': '71250', 'charge_amount': 250.0,
}


class TestDenialApi:
    def test_queue_requires_billing_read(self):
        client = TestClient(_make_app(_user()))
        resp = client.get('/ris/billing/denials')
        assert resp.status_code == 403

    def test_queue_lists_denied_claims(self):
        client = TestClient(_make_app(_user('BILLING_READ')))
        conn = _Conn()
        conn.set_fetch([_DENIED_ROW])
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.get('/ris/billing/denials')
        assert resp.status_code == 200, resp.text
        rows = resp.json()['data']
        assert rows[0]['rejection_code'] == 'CO-16'
        # R2-02-04: rework rows surface the prior-auth linkage.
        assert rows[0]['prior_auth_number'] == 'AUTH-77'

    def test_import_records_parsed_code_not_stub(self):
        """R2-02-01: real 835-style intake replaces the fixed DEN-001."""
        client = TestClient(_make_app(_user('BILLING_WRITE')))
        conn = _Conn()
        conn.set_fetchrow({'id': 'clm-9', 'status': 'DENIED'})
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/denials/import', json={
                'claim_id': 'clm-9',
                'claim_adjustment_reason_code': 'CO-97',
                'reason_text': 'Included in another service',
            })
        assert resp.status_code == 200, resp.text
        updates = [c for c in conn.calls if 'UPDATE ris_claims' in c[1]]
        assert updates, 'import must mark the claim denied'
        assert 'CO-97' in [str(a) for a in updates[0][2]]
        events = [c for c in conn.calls
                  if 'INSERT INTO ris_claim_events' in c[1]]
        assert events, 'intake must log a history event'

    def test_import_unknown_claim_404(self):
        client = TestClient(_make_app(_user('BILLING_WRITE')))
        conn = _Conn()
        conn.set_fetchrow(None)
        with patch('api.billing.get_conn', return_value=conn):
            resp = client.post('/ris/billing/denials/import', json={
                'claim_id': 'nope', 'code': 'CO-16'})
        assert resp.status_code == 404

    def test_resubmit_requires_billing_write(self):
        client = TestClient(_make_app(_user('BILLING_READ')))
        resp = client.post('/ris/billing/claims/clm-9/resubmit',
                           json={'note': 'x'})
        assert resp.status_code == 403

    def test_resubmit_returns_submitted(self):
        client = TestClient(_make_app(_user('BILLING_WRITE')))
        conn = _Conn()
        with patch('api.billing.get_conn', return_value=conn), \
             patch('db.ris_charges.RisClaims.correct_and_resubmit',
                   AsyncMock(return_value={'id': 'clm-9',
                                           'status': 'SUBMITTED'})):
            resp = client.post('/ris/billing/claims/clm-9/resubmit',
                               json={'note': 'corrected units'})
        assert resp.status_code == 200, resp.text
        assert resp.json()['status'] == 'SUBMITTED'

    def test_resubmit_unknown_claim_404(self):
        client = TestClient(_make_app(_user('BILLING_WRITE')))
        conn = _Conn()

        async def _raise(*a, **kw):
            return None

        with patch('api.billing.get_conn', return_value=conn), \
             patch('db.ris_charges.RisClaims.correct_and_resubmit',
                   AsyncMock(return_value=None)):
            resp = client.post('/ris/billing/claims/nope/resubmit',
                               json={'note': 'x'})
        assert resp.status_code == 404

    def test_history_endpoint(self):
        client = TestClient(_make_app(_user('BILLING_READ')))
        conn = _Conn()
        with patch('api.billing.get_conn', return_value=conn), \
             patch('db.ris_charges.RisClaims.get_history',
                   AsyncMock(return_value=[{'event_type': 'DENIED'}])):
            resp = client.get('/ris/billing/claims/clm-9/history')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['event_type'] == 'DENIED'


# ---------------------------------------------------------------------------
# R2-01-08 — prior-auth number rides the claim line
# ---------------------------------------------------------------------------

class TestAuthOnClaimLine:
    @pytest.mark.asyncio
    async def test_submit_persists_prior_auth(self):
        from db.ris_charges import RisClaims

        conn = _Conn()
        claims = RisClaims(conn)
        with patch.object(claims, 'fetchone',
                          AsyncMock(return_value={'id': 'clm-1',
                                                  'status': 'SUBMITTED'})):
            await claims.submit(
                'chg-1', 'CLM-1', payer_id='P1', payer_name='Aetna',
                tenant_id='default', prior_auth_number='AUTH-77')
        inserts = [sql for _, sql, *_ in conn.calls
                   if 'INSERT INTO ris_claims' in sql]
        assert inserts, 'submit must INSERT'
        assert 'prior_auth_number' in inserts[0]


# ---------------------------------------------------------------------------
# Real-DB chain (R2-02-13a): drop -> submit -> deny -> queue -> resubmit
# ---------------------------------------------------------------------------

class TestDenialChainRealDb:
    @pytest.fixture(autouse=True)
    async def _db(self):
        import db.conn as database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.teardown()

    @pytest.mark.asyncio
    async def test_full_rework_roundtrip(self):
        from datetime import datetime, timezone
        from db.conn import get_conn, set_tenant_slug, reset_tenant_slug
        from db.ris_charges import (
            RisCharges, RisClaims, parse_denial,
        )

        tag = f'rw-{__import__("uuid").uuid4().hex[:6]}'
        set_tenant_slug(tag)
        try:
            async with get_conn() as conn:
                charge = await RisCharges(conn).create(
                    report_id=None, exam_id=None,
                    accession_number=f'ACC-{tag}',
                    patient_id=f'P-{tag}', patient_name='Rework Roundtrip',
                    cpt_code='71250',
                    charge_amount=250.0, tenant_id=tag)
                charge = await conn.fetchrow(
                    'SELECT id FROM ris_charges '
                    'WHERE accession_number = $1 AND tenant_id = $2',
                    f'ACC-{tag}', tag)
                claim = await RisClaims(conn).submit(
                    charge['id'], f'CLM-{tag}', payer_name='Medicare',
                    tenant_id=tag, prior_auth_number='AUTH-E2E')

                parsed = parse_denial({
                    'claim_adjustment_reason_code': 'CO-16',
                    'reason_text': 'Missing contrast documentation',
                })
                await RisClaims(conn).record_denial_with_event(
                    claim['id'], parsed['code'], parsed['reason'],
                    tenant_id=tag)

                queue = await RisClaims(conn).list_rework(tag)
                match = [r for r in queue if r['id'] == claim['id']]
                assert match, 'denied claim must appear in the rework queue'
                assert match[0]['rejection_code'] == 'CO-16'
                assert match[0]['prior_auth_number'] == 'AUTH-E2E'

                resub = await RisClaims(conn).correct_and_resubmit(
                    claim['id'], note='contrast docs attached',
                    actor='coder-9', tenant_id=tag)
                assert resub is not None and resub['status'] == 'SUBMITTED'

                after = await RisClaims(conn).get(claim['id'], tag)
                assert after['correction_count'] == 1
                assert after['resubmitted_at'] is not None

                history = await RisClaims(conn).get_history(claim['id'], tag)
                types = {r['event_type'] for r in history}
                assert {'DENIED', 'CORRECTION'} <= types
        finally:
            reset_tenant_slug()

    @pytest.mark.asyncio
    async def test_claim_events_tenant_tagged(self):
        """S12-08 net: the history ledger carries the tenant tag."""
        import uuid
        from db.conn import get_conn, set_tenant_slug, reset_tenant_slug
        from db.ris_charges import RisCharges, RisClaims

        tag = f'rw-{uuid.uuid4().hex[:6]}'
        set_tenant_slug(tag)
        try:
            async with get_conn() as conn:
                charge = await RisCharges(conn).create(
                    report_id=None, exam_id=None,
                    accession_number=f'ACC-{tag}',
                    patient_id=f'P-{tag}', patient_name='Tag Check',
                    cpt_code='70551',
                    charge_amount=400.0, tenant_id=tag)
                charge = await conn.fetchrow(
                    'SELECT id FROM ris_charges '
                    'WHERE accession_number = $1 AND tenant_id = $2',
                    f'ACC-{tag}', tag)
                claim = await RisClaims(conn).submit(
                    charge['id'], f'CLM-{tag}', tenant_id=tag)
                await RisClaims(conn).record_denial_with_event(
                    claim['id'], 'CO-50', 'Not medically necessary',
                    tenant_id=tag)
                row = await conn.fetchrow(
                    "SELECT tenant_id FROM ris_claim_events "
                    "WHERE claim_id = $1 LIMIT 1",
                    claim['id'],
                )
                assert row is not None
                assert row['tenant_id'] == tag
        finally:
            reset_tenant_slug()
