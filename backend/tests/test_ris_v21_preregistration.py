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
