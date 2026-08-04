from unittest.mock import AsyncMock, patch

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
        mock_conn.fetchrow.return_value = {
            'id': 1, 'patient_id': 'P001', 'name': 'Test Patient',
            'birth_date': '1990-01-01', 'sex': 'F',
        }
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.post('/patients', json={
                'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data['data']['patient_id'] == 'P001'
        assert data['data']['name'] == 'Test Patient'

    def test_create_generates_patient_id_when_empty(self):
        user = User({'id': 1, 'permissions': ['REGISTRATION_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
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
        mock_conn.fetchval.side_effect = [1, 0, 'wl-uuid']
        mock_conn.fetchrow.side_effect = [
            {
                'id': 1, 'patient_id': 'P001', 'name': 'Test Patient',
                'birth_date': '1990-01-01', 'sex': 'F',
            },
            {
                'id': 'appt-1', 'patient_id': 'P001', 'visit_id': None,
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
        mock_conn.fetchrow.return_value = {'id': 'appt-1'}
        with patch('api.frontdesk.get_conn', return_value=mock_conn):
            resp = client.delete('/appointments/appt-1')
        assert resp.status_code == 200
