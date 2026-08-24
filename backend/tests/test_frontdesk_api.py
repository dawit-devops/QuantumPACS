from unittest.mock import AsyncMock, MagicMock, patch
from datetime import time

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


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
    from api.frontdesk import (
        AppointmentAvailabilityHandler, AppointmentHandler, AppointmentsHandler,
        ConsentsHandler, InsuranceHandler, PatientsRegistrationHandler,
        PatientsSearchHandler, VisitHandler, VisitOrdersHandler, VisitsHandler,
        WaitingQueueHandler,
    )
    return Starlette(
        routes=[
            Route('/patients/search', endpoint=PatientsSearchHandler),
            Route('/patients', endpoint=PatientsRegistrationHandler),
            Route('/visits', endpoint=VisitsHandler),
            Route('/visits/{id}', endpoint=VisitHandler),
            Route('/visits/{id}/orders', endpoint=VisitOrdersHandler),
            Route('/schedule/availability', endpoint=AppointmentAvailabilityHandler),
            Route('/appointments', endpoint=AppointmentsHandler),
            Route('/appointments/{id}', endpoint=AppointmentHandler),
            Route('/visits/{id}/consents', endpoint=ConsentsHandler),
            Route('/visits/{id}/consents/attach', endpoint=ConsentsHandler),
            Route('/patients/{id}/insurance', endpoint=InsuranceHandler),
            Route('/insurance/{id}', endpoint=InsuranceHandler),
            Route('/queue', endpoint=WaitingQueueHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestPatientRegistration:
    def test_create_requires_registration_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/patients', json={'name': 'Test Patient'})
        assert resp.status_code == 403

    def test_create_success(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        # dedup pre-check misses first, then the insert returns the new row
        mock_conn.fetchrow.side_effect = [
            None,
            {
                'id': 1, 'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/patients', json={
                'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data['data']['patient_id'] == 'P001'
        assert data['data']['name'] == 'Test Patient'
        # exactly one dedup probe + one insert
        assert mock_conn.fetchrow.await_count == 2

    def test_create_duplicate_name_birth_date_returns_409(self):
        """R5-13: registering the same person twice (different MRN) must be
        rejected server-side with the existing record — dedup is not a
        client-side banner."""
        user = User({'id': 1, 'permissions': ['REGISTRATION_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            {
                'id': 7, 'patient_id': 'P999', 'name': 'Jane Doe',
                'birth_date': '1980-01-01', 'sex': 'F',
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/patients', json={
                'patient_id': 'NEW1', 'name': 'Jane Doe',
                'birth_date': '1980-01-01', 'sex': 'F',
            })
        assert resp.status_code == 409
        err = resp.json()['error']
        assert err['code'] == 'PATIENT_EXISTS'
        assert err['details']['patient']['patient_id'] == 'P999'
        # no insert attempted — only the dedup probe ran
        assert mock_conn.fetchrow.await_count == 1

    def test_create_generates_patient_id_when_empty(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {
            'id': 2, 'patient_id': 'P1234567890', 'name': 'Gen Patient',
            'birth_date': '', 'sex': '',
        }
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/patients', json={'name': 'Gen Patient'})
        assert resp.status_code == 201
        assert resp.json()['data']['patient_id'].startswith('P')


class TestPatientSearch:
    def test_search_requires_registration_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/patients/search?q=te')
        assert resp.status_code == 403

    def test_search_returns_empty_below_min_query_length(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_READ']})
        client = TestClient(_make_app(user))
        resp = client.get('/patients/search?q=t')
        assert resp.status_code == 200
        assert resp.json()['data'] == []

    def test_search_success(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {
                'id': 1, 'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.get('/patients/search?q=te')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 1
        assert data['data'][0]['patient_id'] == 'P001'


class TestAppointmentConflict:
    def test_post_requires_schedule_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/appointments', json={})
        assert resp.status_code == 403

    def test_post_conflict_returns_409(self):
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.side_effect = [1, 1]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/appointments', json={
                'patient_id': 'P001',
                'modality': 'CT',
                'scheduled_date': '2026-08-10',
                'scheduled_time': '09:00:00',
            })
        assert resp.status_code == 409
        assert 'already booked' in resp.json()['error']['message'].lower()

    def test_post_success(self):
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.side_effect = [1, 0, 'wl-uuid']
        mock_conn.fetchrow.side_effect = [
            {
                'id': 1, 'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            },
            {
                'id': 'appt-1', 'patient_id': 'P001', 'visit_id': None,
                'worklist_entry_id': 'wl-uuid',
                'modality': 'CT', 'room': 'CT1', 'technologist': '',
                'scheduled_date': '2026-08-10', 'scheduled_time': '09:00:00',
                'status': 'scheduled',
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/appointments', json={
                'patient_id': 'P001',
                'modality': 'CT',
                'scheduled_date': '2026-08-10',
                'scheduled_time': '09:00:00',
            })
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['id'] == 'appt-1'
        assert data['worklist_entry_id'] == 'wl-uuid'
        # the appointment insert carries the worklist entry id (R5-08)
        appt_sql, *appt_args = mock_conn.fetchrow.await_args_list[-1].args
        assert 'worklist_entry_id' in appt_sql
        assert appt_args[2] == 'wl-uuid'

    def test_post_phantom_patient_returns_404(self):
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.side_effect = [1, 0]
        mock_conn.fetchrow.return_value = None
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/appointments', json={
                'patient_id': 'NOPE',
                'modality': 'CT',
                'scheduled_date': '2026-08-10',
                'scheduled_time': '09:00:00',
            })
        assert resp.status_code == 404
        assert resp.json()['error']['message'] == 'Patient not found'
        # capacity + booked only — nothing was inserted for an unknown patient
        assert mock_conn.fetchval.await_count == 2
        assert mock_conn.fetchrow.await_count == 1


class TestWaitingQueuePrivacy:
    def test_queue_requires_queue_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/queue')
        assert resp.status_code == 403

    def test_queue_projects_privacy_fields(self):
        user = User({'id': 1, 'permissions': ['QUEUE_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {
                'visit_id': 'v1', 'patient_id': 'MRN12345',
                'patient_name': 'John Smith', 'status': 'checked_in',
                'destination': 'CT1', 'updated_at': '2026-08-04T10:00:00+00:00',
            },
            {
                'visit_id': 'v2', 'patient_id': 'P1',
                'patient_name': '', 'status': 'registered',
                'destination': '', 'updated_at': '2026-08-04T10:00:00+00:00',
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.get('/queue?date=2026-08-04')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 2
        row = data[0]
        assert row['initials'] == 'J.S.'
        assert row['last4'] == '2345'
        assert row['status'] == 'checked_in'
        assert row['destination'] == 'CT1'
        assert row['visit_id'] == 'v1'
        assert 'patient_name' not in row
        assert 'name' not in row
        assert 'patient_id' not in row
        assert data[1]['initials'] == ''
        assert data[1]['last4'] == 'P1'

    def test_queue_exposes_wait_minutes(self):
        # FD-05: the front-desk queue needs minutes-since-arrival so the UI
        # can color-code by wait time (green <15m, amber 15-30m, red >30m).
        user = User({'id': 1, 'permissions': ['QUEUE_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {
                'visit_id': 'v1', 'patient_id': 'MRN12345',
                'patient_name': 'John Smith', 'status': 'checked_in',
                'destination': 'CT1', 'updated_at': '2026-08-04T10:00:00+00:00',
                'wait_minutes': 22,
            },
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.get('/queue?date=2026-08-04')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['wait_minutes'] == 22


class TestVisitStatusTransitions:
    """R5-10: the server enforces the one canonical visit lifecycle —
    registered → checked_in → in_progress → complete, terminal at complete."""

    def _client(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_WRITE']})
        return TestClient(_make_app(user))

    def _conn(self, status):
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'v1', 'status': status}
        return mock_conn

    def test_legal_transition_succeeds(self):
        client = self._client()
        mock_conn = self._conn('registered')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'status': 'checked_in'})
        assert resp.status_code == 200
        assert mock_conn.execute.await_count == 2  # update + audit

    def test_skip_transition_rejected(self):
        """registered → in_progress skips check-in and must be refused."""
        client = self._client()
        mock_conn = self._conn('registered')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'status': 'in_progress'})
        assert resp.status_code == 409
        err = resp.json()['error']
        assert err['code'] == 'INVALID_VISIT_TRANSITION'
        assert 'registered -> in_progress' in err['message']
        # no write happened — transition validated before the UPDATE
        assert mock_conn.execute.await_count == 0

    def test_no_transition_out_of_complete(self):
        client = self._client()
        mock_conn = self._conn('complete')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'status': 'checked_in'})
        assert resp.status_code == 409
        assert resp.json()['error']['code'] == 'INVALID_VISIT_TRANSITION'

    def test_same_status_is_idempotent(self):
        client = self._client()
        mock_conn = self._conn('checked_in')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'status': 'checked_in'})
        assert resp.status_code == 200

    def test_unknown_status_string_rejected(self):
        client = self._client()
        mock_conn = self._conn('registered')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'status': 'archived'})
        assert resp.status_code == 422
        # the validation failure short-circuits before any DB call
        assert mock_conn.fetchrow.await_count == 0

    def test_non_status_update_bypasses_transition_check(self):
        """Changing the room is not a lifecycle transition."""
        client = self._client()
        mock_conn = self._conn('complete')
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.put('/visits/v1', json={'destination_room': 'MR2'})
        assert resp.status_code == 200


class TestAppointmentAvailability:
    def test_requires_schedule_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/schedule/availability?modality=CT&date=2026-08-10')
        assert resp.status_code == 403

    def test_counts_appointments_only(self):
        """Booked capacity comes from appointments alone (R5-01) — the
        mirrored worklist entry must not double-count the same booking."""
        user = User({'id': 1, 'permissions': ['SCHEDULE_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 2
        mock_conn.fetch.return_value = [
            {'scheduled_time': time(9, 0), 'c': 2},
        ]
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.get('/schedule/availability?modality=CT&date=2026-08-10')
        assert resp.status_code == 200
        slots = {s['time']: s for s in resp.json()['data']}
        assert slots['09:00']['booked'] == 2
        assert slots['09:00']['state'] == 'full'
        # single-source: exactly one aggregation query runs
        assert mock_conn.fetch.await_count == 1

    def test_unconfigured_modality_returns_404(self):
        """R5-16: a modality with no capacity row must be reported as not
        configured — previously it silently booked at capacity 1."""
        user = User({'id': 1, 'permissions': ['SCHEDULE_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = None
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.get('/schedule/availability?modality=NM&date=2026-08-10')
        assert resp.status_code == 404
        assert resp.json()['error']['message'] == 'Modality not configured for this day'

    def test_appointment_booking_unconfigured_modality_returns_404(self):
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = None
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/appointments', json={
                'patient_id': 'P001',
                'modality': 'NM',
                'scheduled_date': '2026-08-10',
                'scheduled_time': '09:00:00',
            })
        assert resp.status_code == 404
        assert 'not configured' in resp.json()['error']['message']
        # nothing inserted — advisory lock only
        assert mock_conn.fetchrow.await_count == 0

    def test_invalid_modality_rejected(self):
        """R5-16: the server owns the canonical modality vocabulary — a
        free-form string would silently miss its capacity configuration."""
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/appointments', json={
                'patient_id': 'P001',
                'modality': 'ct',
                'scheduled_date': '2026-08-10',
                'scheduled_time': '09:00:00',
            })
        assert resp.status_code == 422


class TestAppointmentCancel:
    def test_cancel_requires_schedule_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.delete('/appointments/appt-1')
        assert resp.status_code == 403

    def test_cancel_success(self):
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'appt-1'}
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.delete('/appointments/appt-1')
        assert resp.status_code == 200

    def test_cancel_cascades_to_worklist_entry(self):
        """Cancelling an appointment must also cancel its mirrored worklist
        entry so the modality worklist stops showing the patient (R5-02)."""
        user = User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': 'appt-1'}
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.delete('/appointments/appt-1')
        assert resp.status_code == 200
        # appointment update + worklist cascade + audit insert
        assert mock_conn.execute.await_count == 3
        wl_sqls = [
            call.args[0] for call in mock_conn.execute.await_args_list
            if 'worklist_entries' in call.args[0]
        ]
        assert len(wl_sqls) == 1
        assert "'cancelled'" in wl_sqls[0]
