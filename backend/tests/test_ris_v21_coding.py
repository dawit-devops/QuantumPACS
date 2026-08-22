"""v2.1 R2-06-01/02/03 — coding suggestion completion + pilot telemetry.

The auto-drop filled CPT but never consulted the report's indication for
an ICD-10 (suggest_icd10 existed unused). Coders could edit codes in the
queue, but overrides were invisible: no audit event, no counters — the
>= 90% acceptance gate was unmeasurable. This suite closes both.
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
    from api.billing import RisChargeDropHandler

    return Starlette(
        routes=[Route('/ris/billing/charges/{id}/drop',
                      endpoint=RisChargeDropHandler, methods=['POST'])],
        middleware=[Middleware(_FakeAuth,
                               user=user or User({'id': 5, 'tenant': 'default',
                                                  'permissions': ['*'],
                                                  'admin': True}))],
    )


_CHARGE = {
    'id': 'chg-1', 'tenant_id': 'default', 'status': 'PENDING',
    'cpt_code': '71250', 'icd10_code': '',
    'report_id': 'rep-1', 'created_at': None,
}


class TestIcdFromReport:
    """R2-06-01 residual: the auto-drop must consult the indication too."""

    @pytest.mark.asyncio
    async def test_drop_charge_falls_back_to_indication_icd(self):
        from db.ris_charges import drop_charge

        conn = AsyncMock()
        inserted = {}

        class _Charges:
            async def create(self, **kw):
                inserted.update(kw)
                return {'id': 'chg-new'}

        with patch('db.ris_charges.RisCharges', return_value=_Charges()), \
             patch('db.ris_coding.CodingService') as CS:
            svc = CS.return_value
            svc.get_suggestions = AsyncMock(
                return_value={'cpt_code': '71250',
                              'cpt_description': 'CT chest'})
            svc.suggest_icd10 = AsyncMock(
                return_value={'icd10_code': 'R91.1'})
            await drop_charge(conn, report_id='rep-1', exam_id=1,
                              accession_number='ACC-1', patient_id='P',
                              procedure_desc='CT Chest',
                              indication='cough, hemoptysis',
                              tenant_id='default')
        svc.suggest_icd10.assert_awaited_once_with(
            'cough, hemoptysis', 'default')
        assert inserted['icd10_code'] == 'R91.1'

    @pytest.mark.asyncio
    async def test_procedure_cpt_wins_no_icd_crash(self):
        from db.ris_charges import drop_charge

        conn = AsyncMock()
        inserted = {}

        class _Charges:
            async def create(self, **kw):
                inserted.update(kw)
                return {'id': 'chg-new'}

        with patch('db.ris_charges.RisCharges', return_value=_Charges()), \
             patch('db.ris_coding.CodingService') as CS:
            svc = CS.return_value
            svc.get_suggestions = AsyncMock(
                return_value={'cpt_code': '71250',
                              'icd10_code': 'J98.4'})
            svc.suggest_icd10 = AsyncMock(return_value={})
            await drop_charge(conn, report_id='r', exam_id=1,
                              accession_number='A', patient_id='P',
                              procedure_desc='CT', indication='',
                              tenant_id='t')
        assert inserted['icd10_code'] == 'J98.4'


class TestOverrideCapture:
    """R2-06-02: a coder's edited code is an audited override event."""

    @pytest.mark.asyncio
    async def test_confirmed_override_audits_and_counts(self):
        client = TestClient(_make_app())
        charge = dict(_CHARGE)
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.side_effect = [charge, {'status': 'BILLED'}]
        events = []

        async def fake_log(self, **kw):
            events.append(kw['event_type'])

        counted = []

        async def fake_inc(kind):
            counted.append(kind)

        with patch('api.billing.get_conn', return_value=conn), \
             patch('db.audit_log.AuditLog.log_event', new=fake_log), \
             patch('services.coding_telemetry.record_outcome',
                   new=fake_inc):
            resp = client.post('/ris/billing/charges/chg-1/drop', json={
                'cpt_code': '71550', 'icd10_code': 'R91.1'})
        assert resp.status_code == 200, resp.text
        assert 'billing.charge_dropped' in events
        assert 'billing.cpt_overridden' in events, \
            'edited code != suggested code must audit as an override'
        assert counted == ['overridden']

    @pytest.mark.asyncio
    async def test_confirm_without_edit_counts_accepted(self):
        client = TestClient(_make_app())
        charge = dict(_CHARGE)
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.side_effect = [charge, {'status': 'BILLED'}]

        async def fake_log(self, **kw):
            pass

        counted = []

        async def fake_inc(kind):
            counted.append(kind)

        with patch('api.billing.get_conn', return_value=conn), \
             patch('db.audit_log.AuditLog.log_event', new=fake_log), \
             patch('services.coding_telemetry.record_outcome',
                   new=fake_inc):
            client.post('/ris/billing/charges/chg-1/drop', json={})
        assert counted == ['accepted']

    def test_acceptance_counters_registered(self):
        from api.telemetry import (
            coding_suggestions_accepted_total,
            coding_suggestions_overridden_total,
        )
        assert coding_suggestions_accepted_total._name == \
            'coding_suggestions_accepted'
        assert coding_suggestions_overridden_total._name == \
            'coding_suggestions_overridden'
