from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import _ValidationException, validation_exception_handler


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.portal import (
        PortalAppointmentsHandler,
        PortalConsentHandler,
        PortalFollowUpHandler,
        PortalFollowUpStatusHandler,
        PortalOrdersHandler,
        PortalPatientHandler,
        PortalPatientSearchHandler,
        PortalReportHandler,
        PortalScopeHandler,
    )
    return Starlette(
        routes=[
            Route('/portal/scope', endpoint=PortalScopeHandler),
            Route('/portal/scope/{id}', endpoint=PortalScopeHandler, methods=['DELETE']),
            Route('/portal/patients', endpoint=PortalPatientSearchHandler),
            Route('/portal/patients/{patient_id}', endpoint=PortalPatientHandler),
            Route(
                '/portal/patients/{patient_id}/reports/{report_id}',
                endpoint=PortalReportHandler,
            ),
            Route('/portal/patients/{patient_id}/orders', endpoint=PortalOrdersHandler),
            Route(
                '/portal/patients/{patient_id}/appointments',
                endpoint=PortalAppointmentsHandler,
            ),
            Route(
                '/portal/patients/{patient_id}/consent',
                endpoint=PortalConsentHandler,
                methods=['PUT'],
            ),
            Route('/portal/follow-ups', endpoint=PortalFollowUpHandler),
            Route(
                '/portal/follow-ups/{id}',
                endpoint=PortalFollowUpStatusHandler,
                methods=['PUT'],
            ),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


STAFF = User({'id': 1, 'permissions': ['PORTAL_READ', 'FOLLOW_UP_WRITE']})
READ_ONLY = User({'id': 2, 'permissions': ['PORTAL_READ']})
NO_PERMS = User({'id': 3, 'permissions': []})
# P-05: patients hold FOLLOW_UP_SELF (self-scoped writes only) — never
# FOLLOW_UP_WRITE, which would let them attach scopes to arbitrary patients
# (R3-01).
PATIENT = User({'id': 4, 'permissions': ['PORTAL_READ', 'FOLLOW_UP_SELF']})


def _scope_row(**over):
    row = {'id': 'scope-1', 'patient_id': 'MRN1', 'scope_type': 'ward'}
    row.update(over)
    return row


def _demo_row(**over):
    row = {
        'patient_id': 'MRN1', 'name': 'Jane^Doe',
        'birth_date': '19900101', 'sex': 'F',
    }
    row.update(over)
    return row


def _order_row(**over):
    row = {
        'id': 'exam-1', 'accession_number': 'ACC001', 'modality': 'CT',
        'requested_procedure_desc': 'CT Head', 'status': 'completed',
        'priority': 'routine', 'created_at': None, 'completed_at': None,
    }
    row.update(over)
    return row


def _report_row(**over):
    row = {
        'report_id': 'rep-1', 'exam_id': 'exam-1', 'accession_number': 'ACC001',
        'signed_at': None, 'signed_by': 'Dr. Radiologist',
        'status': 'final', 'modality': 'CT',
        'impression': 'Normal', 'findings': 'No acute findings',
    }
    row.update(over)
    return row


class TestPortalScope:
    def test_list_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/scope')
        assert resp.status_code == 403

    def test_list_returns_scope_rows(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [_scope_row(name='Jane^Doe')]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/scope')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['patient_id'] == 'MRN1'

    def test_create_requires_follow_up_write(self):
        # R3-01: PORTAL_READ alone (the patient role's grant) must never
        # attach a scope to an arbitrary patient.
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 403

    def test_patient_cannot_attach_scope(self):
        # R3-01: FOLLOW_UP_SELF must not open scope attachment — that stays
        # FOLLOW_UP_WRITE (staff) only.
        client = TestClient(_make_app(PATIENT))
        resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 403

    def test_create_requires_any_permission(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 403

    def test_create_success(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.side_effect = [
            None,
            {'id': 'scope-1', 'scope_type': 'ward'},
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['id'] == 'scope-1'

    def test_create_duplicate_returns_existing(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {'id': 'scope-1', 'scope_type': 'ward'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['existing'] is True
        assert data['id'] == 'scope-1'

    def test_create_duplicate_is_audited(self):
        """R5-14: the idempotent re-attach path is a state confirmation, not
        a no-op — it must leave an audit trail like every other mutation."""
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {'id': 'scope-1', 'scope_type': 'ward'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 200
        audit_calls = [
            call for call in mock_conn.execute.await_args_list
            if 'INSERT INTO logs' in call.args[0]
        ]
        assert len(audit_calls) == 1
        # the event type and patient live in the JSON payload parameter
        payload = audit_calls[0].args[1]
        assert 'portal.scope_exists' in payload
        assert 'MRN1' in payload

    def test_create_unknown_patient_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'NOPE'})
        assert resp.status_code == 404

    def test_delete_own_scope(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'scope-1', 'patient_id': 'MRN1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.delete('/portal/scope/scope-1')
        assert resp.status_code == 200

    def test_delete_other_users_scope_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.delete('/portal/scope/scope-1')
        assert resp.status_code == 404


class TestPortalPatientSearch:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients?q=jo')
        assert resp.status_code == 403

    def test_short_query_returns_empty(self):
        client = TestClient(_make_app(STAFF))
        resp = client.get('/portal/patients?q=j')
        assert resp.status_code == 200
        assert resp.json()['data'] == []

    def test_returns_scoped_rows_only(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [_demo_row()]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients?q=Jane')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['patient_id'] == 'MRN1'
        mock_conn.fetch.assert_awaited_once()


class TestPortalReportFields:
    """S6: list_final_reports must return status, modality, impression,
    and id — the frontend renders these columns and the old SQL omitted
    them, leaving blank cells in ReportList and PortalHome."""

    def test_list_sql_includes_status_modality_impression_id(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        scope_returned = False
        sqls = []

        async def fetchrow(sql, *args):
            nonlocal scope_returned
            if not scope_returned:
                scope_returned = True
                return _scope_row()
            return None  # get_demographics — not our concern

        async def fetch(sql, *args):
            sqls.append(sql)
            return [_report_row()]

        mock_conn.fetchrow = fetchrow
        mock_conn.fetch = fetch
        with patch('api.portal.get_conn', return_value=mock_conn):
            client.get('/portal/patients/MRN1')
        assert sqls, 'no fetch call captured'
        # Capture the report query (second fetch is for list_final_reports)
        report_sql = sqls[1] if len(sqls) > 1 else sqls[0]
        assert 'modality' in report_sql, report_sql
        assert 'status' in report_sql, report_sql
        assert 'impression' in report_sql, report_sql
        # The frontend reads r.id; the SQL must alias it
        assert 'r.id AS id' in report_sql or 'report_id AS id' in report_sql, \
            report_sql


class TestPortalPatientView:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 403

    def test_scoped_view_returns_patient_orders_and_final_reports(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [_scope_row(), _demo_row()]
        mock_conn.fetch.side_effect = [
            [_order_row()],
            [_report_row()],
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['patient']['name'] == 'Jane^Doe'
        assert data['orders'][0]['id'] == 'exam-1'
        assert data['reports'][0]['report_id'] == 'rep-1'

    def test_out_of_scope_returns_null_data(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 200
        assert resp.json()['data'] is None


class TestPortalReportView:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 403

    def test_non_final_report_never_returned(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),
            {'report_id': 'rep-1', 'status': 'draft'},
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 404

    def test_final_report_returned(self):
        client = TestClient(_make_app(STAFF))
        final_row = {
            'report_id': 'rep-1', 'exam_id': 'exam-1', 'status': 'final',
            'accession_number': 'ACC001', 'findings': 'No acute findings',
            'impression': 'Normal', 'recommendations': 'None',
            'signed_by': 'Dr. Radiologist', 'signed_at': None,
        }
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [_scope_row(), final_row]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['findings'] == 'No acute findings'
        assert 'status' not in data

    def test_out_of_scope_returns_null_data(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 200
        assert resp.json()['data'] is None


class TestPortalOrders:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 403

    def test_scoped_orders(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = _scope_row()
        mock_conn.fetch.return_value = [_order_row()]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['accession_number'] == 'ACC001'

    def test_out_of_scope_orders_empty(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 200
        assert resp.json()['data'] == []


class TestPortalAppointments:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1/appointments')
        assert resp.status_code == 403

    def test_scoped_appointments_include_prep_modality_room(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = _scope_row()
        mock_conn.fetch.return_value = [
            {
                'id': 'appt-1', 'patient_id': 'MRN1',
                'start_time': '2026-08-28T10:30:00+00:00',
                'end_time': '2026-08-28T11:00:00+00:00',
                'status': 'SCHEDULED',
                'modality': 'CT', 'room': 'CT-1',
                'prep_instructions': 'Fast for 4 hours before your exam',
                'procedure': 'CT Chest with Contrast',
                'priority': 'ROUTINE', 'accession_number': 'ACC001',
            },
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/appointments')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['status'] == 'SCHEDULED'
        assert data[0]['modality'] == 'CT'
        assert data[0]['room'] == 'CT-1'
        assert data[0]['prep_instructions'] == \
            'Fast for 4 hours before your exam'
        assert data[0]['procedure'] == 'CT Chest with Contrast'

    def test_out_of_scope_appointments_empty(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/appointments')
        assert resp.status_code == 200
        assert resp.json()['data'] == []


class TestPortalConsent:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.put('/portal/patients/MRN1/consent',
                          json={'consent_results': True})
        assert resp.status_code == 403

    def test_grant_consent_updates_meta_and_audits(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),
            {'id': 1},  # consent_granted probe is not used here; set_consent
        ]
        executed = []

        async def execute(sql, *args):
            executed.append(sql)
            return 'UPDATE 1'

        mock_conn.execute = execute
        with patch('api.portal.get_conn', return_value=mock_conn), \
             patch('db.audit_log.AuditLog.log_event', new=AsyncMock()) as alog:
            resp = client.put('/portal/patients/MRN1/consent',
                              json={'consent_results': True})
        assert resp.status_code == 200, resp.text
        assert resp.json()['data']['consent_results'] is True
        assert any("UPDATE patients" in s for s in executed), executed
        assert any("consent_results" in s for s in executed), executed

    def test_revoke_consent_writes_false(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),
        ]
        executed = []

        async def execute(sql, *args):
            executed.append(sql)
            return 'UPDATE 1'

        mock_conn.execute = execute
        with patch('api.portal.get_conn', return_value=mock_conn), \
             patch('db.audit_log.AuditLog.log_event', new=AsyncMock()):
            resp = client.put('/portal/patients/MRN1/consent',
                              json={'consent_results': False})
        assert resp.status_code == 200
        assert any("UPDATE patients" in s for s in executed), executed
        assert any("consent_results" in s for s in executed), executed

    def test_out_of_scope_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/patients/MRN1/consent',
                              json={'consent_results': True})
        assert resp.status_code == 404


class TestPortalFollowUps:
    def test_list_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/follow-ups')
        assert resp.status_code == 403

    def test_list_returns_own_follow_ups(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [{
            'id': 'fu-1', 'report_id': None, 'exam_id': 'exam-1',
            'patient_id': 'MRN1', 'reason': 'Repeat CT', 'status': 'submitted',
            'priority': 'stat', 'assigned_to': '', 'created_at': None,
            'updated_at': None, 'accession_number': 'ACC001',
        }]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/follow-ups')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data[0]['accession_number'] == 'ACC001'

    def test_list_filters_by_status(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        with patch('api.portal.get_conn', return_value=mock_conn):
            client.get('/portal/follow-ups?status=submitted')
        call = mock_conn.fetch.call_args
        assert 'submitted' in call.args
    def test_create_requires_follow_up_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/portal/follow-ups', json={
            'patient_id': 'MRN1', 'reason': 'Repeat imaging',
        })
        assert resp.status_code == 403

    def test_patient_with_follow_up_self_can_create(self):
        # P-05: a patient may file a follow-up against their own scoped
        # patient via FOLLOW_UP_SELF — no FOLLOW_UP_WRITE needed.
        client = TestClient(_make_app(PATIENT))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),          # get_scope — in scope
            {'id': 'fu-1'},        # create_follow_up
        ]
        mock_conn.fetchval.return_value = 1  # follow_up_targets_valid
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role') as mock_notify:
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'reason': 'Question about my results',
                    'priority': 'routine',
                })
        assert resp.status_code == 201
        assert resp.json()['data']['id'] == 'fu-1'
        mock_notify.assert_awaited_once()

    def test_create_persists_contact_method_and_note(self):
        # P-05: the coordinator needs the patient's preferred contact info —
        # create_follow_up must INSERT contact_method/note/preferred_time.
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),
            {'id': 'fu-1'},
        ]
        mock_conn.fetchval.return_value = 1
        insert_sql = []

        original_fetchrow = mock_conn.fetchrow
        async def tracked_fetchrow(sql, *args):
            insert_sql.append(sql)
            return await original_fetchrow(sql, *args)

        mock_conn.fetchrow = tracked_fetchrow
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role'):
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'reason': 'Please call me about my results',
                    'priority': 'routine',
                    'contact_method': 'email',
                    'note': 'Prefer email, weekday mornings',
                    'preferred_time': 'morning',
                })
        assert resp.status_code == 201, resp.text
        assert any('contact_method' in s for s in insert_sql), insert_sql
        assert any('note' in s for s in insert_sql), insert_sql
        assert any('preferred_time' in s for s in insert_sql), insert_sql

    def test_create_returns_422_without_reason(self):
        client = TestClient(_make_app(STAFF))
        resp = client.post('/portal/follow-ups', json={'patient_id': 'MRN1'})
        assert resp.status_code == 422

    def test_create_success_notifies_radiologists(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _scope_row(),          # get_scope — in scope
            {'id': 'fu-1'},        # create_follow_up
        ]
        mock_conn.fetchval.return_value = 1  # follow_up_targets_valid
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role') as mock_notify:
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'reason': 'New lesion on follow-up CT',
                    'priority': 'stat',
                })
        assert resp.status_code == 201
        assert resp.json()['data']['id'] == 'fu-1'
        mock_notify.assert_awaited_once()
        args = mock_notify.call_args.args
        assert args[1] == 'radiologist'
        assert 'stat' in args[4]

    def test_create_out_of_scope_not_found(self):
        # R3-02: the follow-up write path must respect the scope boundary.
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None  # get_scope — no scope
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role') as mock_notify:
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'reason': 'Repeat imaging',
                })
        assert resp.status_code == 404
        mock_notify.assert_not_awaited()

    def test_create_foreign_report_rejected(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = _scope_row()
        mock_conn.fetchval.return_value = None  # targets_valid — foreign report
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role') as mock_notify:
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'report_id': 'rep-other',
                    'reason': 'Repeat imaging',
                })
        assert resp.status_code == 400
        mock_notify.assert_not_awaited()

    def test_update_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.put('/portal/follow-ups/fu-1', json={'status': 'cancelled'})
        assert resp.status_code == 403

    def test_patient_can_cancel_own_follow_up(self):
        # P-05: cancel-before-in-progress is a patient action via
        # FOLLOW_UP_SELF — the PUT gate accepts either write grant.
        client = TestClient(_make_app(PATIENT))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'fu-1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/follow-ups/fu-1',
                              json={'status': 'cancelled'})
        assert resp.status_code == 200

    def test_update_own_follow_up_success(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'fu-1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/follow-ups/fu-1', json={'status': 'cancelled'})
        assert resp.status_code == 200

    def test_update_other_users_follow_up_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/follow-ups/fu-1', json={'status': 'completed'})
        assert resp.status_code == 404


class TestReleasePolicyRealDb:
    """A4 (GAP_AUDIT_TDD_PIPELINE.md): the HIM hold gate (R2-05-05,
    migration 084) was enforced only in FHIR DR search — Portal.list/
    get_final_report served any final report regardless of release_status,
    so a HIM-held report stayed patient-visible. Held must vanish from the
    patient surfaces; blocked detail views are audited."""

    @pytest.fixture(autouse=True)
    async def setup_db(self):
        from db.conn import database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.close()

    async def _seed(self, conn, tag):
        from db.reports import Reports
        mrn = f'MRN-A4-{tag}'
        await conn.execute(
            "INSERT INTO patients (patient_id, name, birth_date, sex, meta)"
            " VALUES ($1, 'A4 Patient', '1980-01-01', 'F',"
            " jsonb_build_object('consent_results', true))"
            " ON CONFLICT (patient_id) DO NOTHING",
            mrn,
        )
        await conn.execute(
            "INSERT INTO patient_staff_scope (patient_id, user_id,"
            " scope_type, assigned_by) VALUES ($1, 1, 'ward', 1)"
            " ON CONFLICT (patient_id, user_id) DO NOTHING",
            mrn,
        )
        report_ids = {}
        for kind in ('auto', 'held'):
            exam_row = await conn.fetchrow(
                "INSERT INTO exams (accession_number, patient_id, status,"
                " modality) VALUES ($1, $2, 'completed', 'CT')"
                " RETURNING id",
                f'ACC-A4-{kind}-{tag}', mrn,
            )
            report = await Reports(conn).create(
                exam_row['id'],
                {'status': 'draft', 'findings': f'f-{kind}',
                 'impression': f'i-{kind}'},
                created_by='rad-1',
            )
            await Reports(conn).sign(report['id'], signed_by='rad-1')
            if kind == 'held':
                await Reports(conn).set_release_status(
                    str(report['id']), 'held')
            report_ids[kind] = report['id']
        return mrn, report_ids

    async def _cleanup(self, conn, tag):
        mrn = f'MRN-A4-{tag}'
        await conn.execute(
            "DELETE FROM reports WHERE exam_id IN"
            " (SELECT id FROM exams WHERE accession_number LIKE 'ACC-A4-%')"
        )
        await conn.execute(
            "DELETE FROM exams WHERE accession_number LIKE 'ACC-A4-%'")
        await conn.execute(
            "DELETE FROM patient_staff_scope WHERE patient_id = $1", mrn)
        await conn.execute("DELETE FROM patients WHERE patient_id = $1", mrn)

    @pytest.mark.asyncio
    async def test_held_report_absent_from_portal_list(self):
        import uuid
        from db.conn import get_conn
        from db.portal import Portal

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_ids = await self._seed(conn, tag)
            try:
                rows = await Portal(conn).list_final_reports(mrn)
                listed = {str(r['report_id']) for r in rows}
                assert str(report_ids['held']) not in listed, (
                    'HIM-held report leaked into the patient-facing list')
                assert str(report_ids['auto']) in listed
            finally:
                await self._cleanup(conn, tag)

    @pytest.mark.asyncio
    async def test_held_report_get_returns_none(self):
        import uuid
        from db.conn import get_conn
        from db.portal import Portal

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_ids = await self._seed(conn, tag)
            try:
                got = await Portal(conn).get_final_report(
                    mrn, str(report_ids['held']))
                assert got is None, (
                    'HIM-held report must never leave the detail endpoint')
                got_ok = await Portal(conn).get_final_report(
                    mrn, str(report_ids['auto']))
                assert got_ok is not None
            finally:
                await self._cleanup(conn, tag)

    @pytest.mark.asyncio
    async def test_held_detail_view_is_audited_as_blocked(self):
        import uuid
        import httpx
        from db.conn import get_conn
        from starlette.applications import Starlette
        from starlette.routing import Route
        from api.portal import PortalReportHandler

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_ids = await self._seed(conn, tag)
        app = Starlette(
            routes=[Route(
                '/portal/patients/{patient_id}/reports/{report_id}',
                endpoint=PortalReportHandler)],
            middleware=[Middleware(_FakeAuth, user=User(
                {'id': 1, 'permissions': ['PORTAL_READ']}))],
        )
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                    transport=transport, base_url='http://test') as client:
                resp = await client.get(
                    f'/portal/patients/{mrn}/reports/{report_ids["held"]}')
            assert resp.status_code == 404, resp.text

            async with get_conn() as conn:
                blocked = await conn.fetchval(
                    "SELECT 1 FROM logs WHERE log::jsonb->>'event' ="
                    " 'portal.report_hold_blocked'"
                    " AND log::jsonb->'resource'->>'id' = $1"
                    " ORDER BY created DESC LIMIT 1",
                    str(report_ids['held']),
                )
                assert blocked, (
                    'a held-report detail attempt must be audited as '
                    'portal.report_hold_blocked')
        finally:
            async with get_conn() as conn:
                await self._cleanup(conn, tag)


class TestConsentGateRealDb:
    """E1 (GAP_AUDIT_TDD_PIPELINE.md): patient-facing portal reads had no
    consent model (R2-05-07 acceptance). A patient without consent_results
    must not surface reports/orders/demographics; granting consent makes
    them visible; withdrawal revokes future access."""

    @pytest.fixture(autouse=True)
    async def setup_db(self):
        from db.conn import database
        try:
            await database.setup()
        except Exception:
            pytest.skip('dev database unavailable')
        yield
        await database.close()

    async def _seed(self, conn, tag, consent=None):
        mrn = f'MRN-E1-{tag}'
        if consent is None:
            meta_sql = "'{}'::jsonb"
            params = [mrn]
        else:
            meta_sql = "jsonb_build_object('consent_results', $2::boolean)"
            params = [mrn, consent]
        await conn.execute(
            f"INSERT INTO patients (patient_id, name, birth_date, sex, meta)"
            f" VALUES ($1, 'E1 Patient', '1980-01-01', 'F', {meta_sql})",
            *params,
        )
        await conn.execute(
            "INSERT INTO patient_staff_scope (patient_id, user_id,"
            " scope_type, assigned_by) VALUES ($1, 1, 'ward', 1)"
            " ON CONFLICT (patient_id, user_id) DO NOTHING",
            mrn,
        )
        exam_row = await conn.fetchrow(
            "INSERT INTO exams (accession_number, patient_id, status,"
            " modality) VALUES ($1, $2, 'completed', 'CT') RETURNING id",
            f'ACC-E1-{tag}', mrn,
        )
        from db.reports import Reports
        report = await Reports(conn).create(
            exam_row['id'],
            {'status': 'draft', 'findings': 'f', 'impression': 'i'},
            created_by='rad-1',
        )
        await Reports(conn).sign(report['id'], signed_by='rad-1')
        return mrn, str(report['id'])

    async def _cleanup(self, conn, tag):
        mrn = f'MRN-E1-{tag}'
        await conn.execute(
            "DELETE FROM reports WHERE exam_id IN"
            " (SELECT id FROM exams WHERE accession_number LIKE 'ACC-E1-%')")
        await conn.execute(
            "DELETE FROM exams WHERE accession_number LIKE 'ACC-E1-%'")
        await conn.execute(
            "DELETE FROM patient_staff_scope WHERE patient_id = $1", mrn)
        await conn.execute("DELETE FROM patients WHERE patient_id = $1", mrn)

    @pytest.mark.asyncio
    async def test_without_consent_patient_surfaces_empty(self):
        import uuid
        from db.conn import get_conn
        from db.portal import Portal

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_id = await self._seed(conn, tag, consent=None)
            try:
                assert await Portal(conn).list_final_reports(mrn) == [], (
                    'no consent -> no reports surfaced')
                assert await Portal(conn).list_orders(mrn) == []
                assert await Portal(conn).get_final_report(mrn, report_id) is None
                assert await Portal(conn).get_demographics(mrn) is None
            finally:
                await self._cleanup(conn, tag)

    @pytest.mark.asyncio
    async def test_consent_granted_makes_patient_visible(self):
        import uuid
        from db.conn import get_conn
        from db.portal import Portal

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_id = await self._seed(conn, tag, consent=True)
            try:
                reports = await Portal(conn).list_final_reports(mrn)
                assert [str(r['report_id']) for r in reports] == [report_id]
                assert await Portal(conn).list_orders(mrn)
                detail = await Portal(conn).get_final_report(mrn, report_id)
                assert detail is not None and str(detail['report_id']) == report_id
                assert await Portal(conn).get_demographics(mrn) is not None
            finally:
                await self._cleanup(conn, tag)

    @pytest.mark.asyncio
    async def test_withdrawal_revokes_future_access(self):
        import uuid
        from db.conn import get_conn
        from db.portal import Portal

        tag = uuid.uuid4().hex[:6]
        async with get_conn() as conn:
            mrn, report_id = await self._seed(conn, tag, consent=True)
            try:
                assert await Portal(conn).list_final_reports(mrn)
                # withdrawal = consent_results flipped off
                await conn.execute(
                    "UPDATE patients SET meta = '{}'::jsonb"
                    " WHERE patient_id = $1", mrn)
                assert await Portal(conn).list_final_reports(mrn) == [], (
                    'withdrawn consent must revoke future access')
            finally:
                await self._cleanup(conn, tag)
