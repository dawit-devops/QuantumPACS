"""v2.1 R2-06-06..08 — pre-registration chain.

S3-20: ADT^Z01 from HIS must land as a patient record AND a visible
appointment stub — today Z01 falls into the unknown-event warning and
front desk re-keys everything. RIS-REG-04: portal kiosk check-in driven
by an HMAC token that embeds tenant + appointment + expiry; no login,
no PHI leak beyond what the kiosk needs.
"""

import json

import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.testclient import TestClient


_Z01 = {
    'message_type': 'ADT',
    'event_type': 'Z01',
    'patient_id': 'P100',
    'patient_name': 'DOE^JOHN',
    'birth_date': '19800504',
    'sex': 'M',
    'sending_facility': 'HIS-MAIN',
    'scheduled_date': '20260825',
    'scheduled_time': '0930',
}


class _Conn:
    def __init__(self):
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.executed.append(sql)


class TestAdtZ01Preregistration:
    @pytest.mark.asyncio
    async def test_z01_upserts_patient_and_books_stub(self):
        from services.ingestion.hl7_server import handle_adt_message

        conn = _Conn()
        patient_mock = MagicMock()
        patient_mock.return_value.insert_or_select = AsyncMock()
        appts = MagicMock()
        appts.return_value.create = AsyncMock(return_value={'id': 'appt-9'})

        with patch('services.ingestion.hl7_server.get_conn',
                   return_value=conn), \
             patch('services.ingestion.hl7_server.Patient', patient_mock), \
             patch('db.ris_appointments.RisAppointments', appts):
            ok = await handle_adt_message(_Z01)
        assert ok is True
        patient_mock.return_value.insert_or_select.assert_awaited_once()
        appts.return_value.create.assert_awaited_once()
        call = appts.return_value.create.await_args
        kw = call.args[0] if call.args else call.kwargs
        assert kw['status'] == 'SCHEDULED'
        assert kw['created_by'] == 'hl7:adt-z01'
        assert kw['start_time'].isoformat().startswith('2026-08-25T09:30')
        assert kw['tenant_id'] == 'his-main'

    @pytest.mark.asyncio
    async def test_z01_without_schedule_still_registers_patient(self):
        from services.ingestion.hl7_server import handle_adt_message

        z = dict(_Z01)
        del z['scheduled_date']
        conn = _Conn()
        patient_mock = MagicMock()
        patient_mock.return_value.insert_or_select = AsyncMock()
        appts = MagicMock()
        appts.return_value.create = AsyncMock()

        with patch('services.ingestion.hl7_server.get_conn',
                   return_value=conn), \
             patch('services.ingestion.hl7_server.Patient', patient_mock), \
             patch('db.ris_appointments.RisAppointments', appts):
            ok = await handle_adt_message(z)
        assert ok is True
        patient_mock.return_value.insert_or_select.assert_awaited_once()
        appts.return_value.create.assert_not_awaited()


def _app():
    from api.checkin import PortalCheckInHandler

    return Starlette(routes=[
        Route('/ris/checkin/{token}', endpoint=PortalCheckInHandler),
    ])


_APPT = {
    'id': 'appt-1', 'tenant_id': 'main-hospital', 'status': 'SCHEDULED',
    'patient_name': 'John Doe', 'modality': 'CT',
    'room': 'CT-1',
    'prep_instructions': 'Fast for 4 hours before your exam',
}


class TestKioskCheckIn:
    def test_valid_token_returns_summary_without_auth(self):
        from api.checkin import PortalCheckInHandler, make_checkin_token

        client = TestClient(_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        async def fetchrow(sql, *args):
            assert 'ris_appointments' in sql
            assert 'ris_resources' in sql  # S1: join for modality/room
            assert 'prep_instructions' in sql  # S1: prep field
            assert "p.name" in sql or 'patients' in sql
            return dict(_APPT)

        conn = MagicMock(fetchrow=fetchrow)
        with patch('api.checkin.get_conn') as gc:
            gc.return_value.__aenter__ = AsyncMock(return_value=conn)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.get(f'/ris/checkin/{token}')
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['patient_name'] == 'John Doe'
        assert body['status'] == 'SCHEDULED'
        # S1: kiosk summary includes modality, room, prep_instructions
        assert body['modality'] == 'CT'
        assert body['room'] == 'CT-1'
        assert body['prep_instructions'] == 'Fast for 4 hours before your exam'

    def test_tampered_token_rejected(self):
        from api.checkin import PortalCheckInHandler, make_checkin_token

        client = TestClient(_app())
        token = make_checkin_token('main-hospital', 'appt-1')
        head, _, sig = token.rpartition('.')
        bad = f'{head}.{sig[:-2]}xx'
        resp = client.get(f'/ris/checkin/{bad}')
        assert resp.status_code == 403

    def test_expired_token_rejected(self):
        from api.checkin import PortalCheckInHandler, make_checkin_token

        client = TestClient(_app())
        token = make_checkin_token('main-hospital', 'appt-1',
                                   ttl_seconds=-60)
        resp = client.get(f'/ris/checkin/{token}')
        assert resp.status_code == 403

    def test_unknown_appointment_404(self):
        from api.checkin import PortalCheckInHandler, make_checkin_token

        client = TestClient(_app())
        token = make_checkin_token('main-hospital', 'ghost')
        with patch('api.checkin.get_conn') as gc:
            gc.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(fetchrow=AsyncMock(
                    return_value=None)))
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.get(f'/ris/checkin/{token}')
        assert resp.status_code == 404

    def test_confirm_marks_checked_in_then_conflicts(self):
        from api.checkin import PortalCheckInHandler, make_checkin_token

        client = TestClient(_app())
        token = make_checkin_token('main-hospital', 'appt-1')
        calls = {'n': 0}

        class _Appts:
            def __init__(self, conn):
                pass

            async def mark_checked_in(self, aid, tenant):
                calls['n'] += 1
                if calls['n'] == 1:
                    return {'id': aid, 'status': 'ARRIVED'}
                return None

        async def noop_log(*a, **k):
            pass

        with patch('api.checkin.get_conn') as gc, \
             patch('db.ris_appointments.RisAppointments', _Appts), \
             patch('db.audit_log.AuditLog.log_event', new=noop_log):
            gc.return_value.__aenter__ = AsyncMock(return_value=None)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            ok = client.post(f'/ris/checkin/{token}')
            dup = client.post(f'/ris/checkin/{token}')
        assert ok.status_code == 200, ok.text
        assert ok.json()['status'] == 'ARRIVED'
        assert dup.status_code == 409


class TestKioskConsent:
    """K-03: the kiosk digital consent form's signature + refusal are
    persisted server-side (S2). The signature is linked to the appointment
    record, stored as base64 PNG; refusal still allows check-in."""

    def _consent_app(self):
        from starlette.routing import Route
        from api.checkin import PortalCheckInConsentHandler

        return Starlette(routes=[
            Route('/ris/checkin/{token}/consent',
                  endpoint=PortalCheckInConsentHandler, methods=['POST']),
        ])

    def test_invalid_token_rejected(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._consent_app())
        token = make_checkin_token('main-hospital', 'appt-1')
        head, _, sig = token.rpartition('.')
        bad = f'{head}.{sig[:-2]}xx'
        resp = client.post(f'/ris/checkin/{bad}/consent', json={
            'accepted': True, 'signature_png': 'data:image/png;base64,AAA=',
        })
        assert resp.status_code == 403

    def test_accept_stores_signature_and_audits(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._consent_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        calls = {'updated': None}
        class _Appts:
            def __init__(self, conn):
                pass

            async def record_consent(self, aid, tenant, accepted,
                                     signature_png, decline_reason):
                calls['updated'] = (aid, tenant, accepted,
                                    signature_png, decline_reason)
                return {'id': aid}

        async def noop_log(*a, **k):
            pass

        with patch('api.checkin.get_conn') as gc, \
             patch('db.ris_appointments.RisAppointments', _Appts), \
             patch('db.audit_log.AuditLog.log_event', new=noop_log):
            gc.return_value.__aenter__ = AsyncMock(return_value=None)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.post(f'/ris/checkin/{token}/consent', json={
                'accepted': True,
                'signature_png': 'data:image/png;base64,AAA=',
            })
        assert resp.status_code == 200, resp.text
        assert calls['updated'] == (
            'appt-1', 'main-hospital', True,
            'data:image/png;base64,AAA=', '',
        )

    def test_decline_with_reason_allows_check_in(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._consent_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        calls = {'updated': None}
        class _Appts:
            def __init__(self, conn):
                pass

            async def record_consent(self, aid, tenant, accepted,
                                     signature_png, decline_reason):
                calls['updated'] = (aid, tenant, accepted,
                                    signature_png, decline_reason)
                return {'id': aid}

        async def noop_log(*a, **k):
            pass

        with patch('api.checkin.get_conn') as gc, \
             patch('db.ris_appointments.RisAppointments', _Appts), \
             patch('db.audit_log.AuditLog.log_event', new=noop_log):
            gc.return_value.__aenter__ = AsyncMock(return_value=None)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.post(f'/ris/checkin/{token}/consent', json={
                'accepted': False,
                'signature_png': '',
                'decline_reason': 'Patient declined to consent',
            })
        assert resp.status_code == 200, resp.text
        assert calls['updated'] == (
            'appt-1', 'main-hospital', False, '',
            'Patient declined to consent',
        )


class TestKioskPayment:
    """K-04 (S4): token-scoped co-pay capture reuses the billing machinery —
    an order-linked invoice is found/created and a payment recorded. The
    kiosk has no login, so the HMAC token is the authorization."""

    def _payment_app(self):
        from starlette.routing import Route
        from api.checkin import PortalCheckInPaymentHandler

        return Starlette(routes=[
            Route('/ris/checkin/{token}/payment',
                  endpoint=PortalCheckInPaymentHandler, methods=['POST']),
        ])

    def test_invalid_token_rejected(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._payment_app())
        token = make_checkin_token('main-hospital', 'appt-1')
        head, _, sig = token.rpartition('.')
        bad = f'{head}.{sig[:-2]}xx'
        resp = client.post(f'/ris/checkin/{bad}/payment', json={
            'method': 'cash', 'amount': 25.0,
            'idempotency_key': 'k1',
        })
        assert resp.status_code == 403

    def test_payment_records_against_order_linked_invoice(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._payment_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        # appointment -> order lookup, then invoice (reused), then payment
        async def fetchrow(sql, *args):
            if 'ris_appointments' in sql:
                return {'id': 'appt-1', 'order_id': 'ord-1',
                        'patient_id': 'MRN1'}
            if 'invoice' in sql and 'order_id' in sql and 'id' not in args:
                return {'id': 'inv-1', 'order_id': 'ord-1',
                        'patient_id': 'MRN1', 'balance': 25.0,
                        'paid_amount': 0.0, 'total_amount': 25.0,
                        'status': 'open'}
            if sql.strip().upper().startswith('SELECT') and 'payment' in sql:
                return None  # no duplicate payment
            if 'receipt' in sql:
                return {'id': 'r-1', 'payment_id': 'pay-1',
                        'receipt_number': 'KPAY-1-01'}
            if 'payment' in sql:
                return {'id': 'pay-1', 'method': 'cash',
                        'amount': 25.0, 'invoice_id': 'inv-1'}
            return {'id': 'pay-1'}

        executed = []
        seen_sql = []
        async def execute(sql, *args):
            executed.append(sql)
            return 'INSERT 0 1'

        orig_fetchrow = fetchrow
        async def tracked_fetchrow(sql, *args):
            seen_sql.append(sql)
            return await orig_fetchrow(sql, *args)

        conn = MagicMock(fetchrow=tracked_fetchrow, execute=execute)
        conn.fetchval = AsyncMock(return_value=None)  # no duplicate payment
        with patch('api.checkin.get_conn') as gc:
            gc.return_value.__aenter__ = AsyncMock(return_value=conn)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('db.audit_log.AuditLog.log_event', new=AsyncMock()):
                resp = client.post(f'/ris/checkin/{token}/payment', json={
                    'method': 'cash', 'amount': 25.0,
                    'idempotency_key': 'kiosk-123',
                })
        assert resp.status_code == 200, resp.text
        body = resp.json()['data']
        assert body['payment']['amount'] == 25.0
        assert body['receipt']['payment_id'] == 'pay-1'
        assert any('UPDATE invoice' in s for s in executed), executed
        assert any('INSERT INTO payment' in s for s in seen_sql), seen_sql


class TestKioskQueuePosition:
    """K-05 (S5): after ARRIVED, the kiosk shows the patient's queue
    position + ETA computed from the same resource's same-day appointments."""

    def _queue_app(self):
        from starlette.routing import Route
        from api.checkin import PortalCheckInQueueHandler

        return Starlette(routes=[
            Route('/ris/checkin/{token}/queue-position',
                  endpoint=PortalCheckInQueueHandler),
        ])

    def test_invalid_token_rejected(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._queue_app())
        token = make_checkin_token('main-hospital', 'appt-1')
        head, _, sig = token.rpartition('.')
        bad = f'{head}.{sig[:-2]}xx'
        resp = client.get(f'/ris/checkin/{bad}/queue-position')
        assert resp.status_code == 403

    def test_returns_position_and_eta(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._queue_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        # appointment lookup -> ahead-of-me count
        async def fetchrow(sql, *args):
            if 'ris_appointments' in sql and 'id::text' in sql:
                return {'id': 'appt-1', 'resource_id': 'res-1',
                        'start_time': '2026-08-28T10:30:00+00:00'}
            return None

        async def fetchval(sql, *args):
            return 2  # two ARRIVED appointments ahead of this one

        conn = MagicMock(fetchrow=fetchrow, fetchval=fetchval)
        with patch('api.checkin.get_conn') as gc:
            gc.return_value.__aenter__ = AsyncMock(return_value=conn)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.get(f'/ris/checkin/{token}/queue-position')
        assert resp.status_code == 200, resp.text
        data = resp.json()['data']
        # 2 ahead + self = position 3
        assert data['position'] == 3
        assert data['eta_minutes'] > 0

    def test_empty_queue_is_position_one(self):
        from api.checkin import make_checkin_token
        client = TestClient(self._queue_app())
        token = make_checkin_token('main-hospital', 'appt-1')

        async def fetchrow(sql, *args):
            if 'ris_appointments' in sql and 'id::text' in sql:
                return {'id': 'appt-1', 'resource_id': 'res-1',
                        'start_time': '2026-08-28T10:30:00+00:00'}
            return None

        async def fetchval(sql, *args):
            return 0

        conn = MagicMock(fetchrow=fetchrow, fetchval=fetchval)
        with patch('api.checkin.get_conn') as gc:
            gc.return_value.__aenter__ = AsyncMock(return_value=conn)
            gc.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.get(f'/ris/checkin/{token}/queue-position')
        assert resp.status_code == 200, resp.text
        assert resp.json()['data']['position'] == 1
