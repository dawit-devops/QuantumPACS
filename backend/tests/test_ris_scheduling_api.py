"""S4-07 — Resource API (B2): create, list, schedules, availability search.

Mock-based endpoint tests in the style of test_ris_orders.py: the public
interface is the HTTP API; permission gates and request/response contracts
are the behavior under test.
"""

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

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
    from api.scheduling import (
        RisResourcesHandler, RisResourceSchedulesHandler, RisResourceAvailabilityHandler,
        RisAppointmentsHandler, RisAppointmentRescheduleHandler, RisAppointmentCancelHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/resources', endpoint=RisResourcesHandler),
            Route('/ris/resources/{id}/schedules', endpoint=RisResourceSchedulesHandler),
            Route('/ris/resources/{id}/availability', endpoint=RisResourceAvailabilityHandler),
            Route('/ris/appointments', endpoint=RisAppointmentsHandler),
            Route('/ris/appointments/{id}/reschedule', endpoint=RisAppointmentRescheduleHandler),
            Route('/ris/appointments/{id}/cancel', endpoint=RisAppointmentCancelHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _resource_row(name='CT Room 1'):
    return {
        'id': 'res-1', 'tenant_id': 'default', 'name': name,
        'resource_type': 'ROOM', 'modality': 'CT', 'location': 'Wing B',
        'status': 'ACTIVE', 'created_at': None,
    }


def _resource_payload(**overrides):
    payload = {
        'name': 'CT Room 1',
        'resource_type': 'ROOM',
        'modality': 'CT',
        'location': 'Wing B',
    }
    payload.update(overrides)
    return payload


class TestResourceCreate:
    def test_create_requires_schedule_write(self):
        client = TestClient(_make_app(user=User({'id': 1, 'permissions': ['SCHEDULE_READ']})))
        resp = client.post('/ris/resources', json=_resource_payload())
        assert resp.status_code == 403

    def test_create_resource_returns_201(self):
        with patch('api.scheduling.get_conn') as conn_ctx, \
             patch('api.scheduling.RisResources') as repo:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            repo.return_value.create = AsyncMock(return_value=_resource_row())
            client = TestClient(_make_app(
                user=User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
            resp = client.post('/ris/resources', json=_resource_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body['data']['name'] == 'CT Room 1'
        assert body['data']['resource_type'] == 'ROOM'

    def test_create_rejects_invalid_type(self):
        client = TestClient(_make_app(
            user=User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
        resp = client.post('/ris/resources', json=_resource_payload(resource_type='CHAIR'))
        assert resp.status_code == 422


class TestResourceList:
    def test_list_requires_schedule_read(self):
        client = TestClient(_make_app(user=User({'id': 1, 'permissions': []})))
        resp = client.get('/ris/resources')
        assert resp.status_code == 403

    def test_list_passes_filters(self):
        with patch('api.scheduling.get_conn') as conn_ctx, \
             patch('api.scheduling.RisResources') as repo:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            repo.return_value.list_for_tenant = AsyncMock(return_value=[_resource_row()])
            client = TestClient(_make_app(
                user=User({'id': 1, 'permissions': ['SCHEDULE_READ']})))
            resp = client.get('/ris/resources?resource_type=ROOM&modality=CT')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['name'] == 'CT Room 1'
        called = repo.return_value.list_for_tenant.await_args
        assert called.kwargs['resource_type'] == 'ROOM'
        assert called.kwargs['modality'] == 'CT'


class TestResourceAvailability:
    def test_availability_requires_schedule_read(self):
        client = TestClient(_make_app(user=User({'id': 1, 'permissions': []})))
        resp = client.get('/ris/resources/res-1/availability?date=2026-08-20')
        assert resp.status_code == 403

    def test_availability_returns_free_slots(self):
        with patch('api.scheduling.get_conn') as conn_ctx, \
             patch('api.scheduling.SchedulingEngine') as engine_cls:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            engine = AsyncMock()
            engine.available_slots = AsyncMock(return_value=[
                {'start': '08:00', 'end': '08:30'},
                {'start': '08:30', 'end': '09:00'},
            ])
            engine_cls.return_value = engine
            client = TestClient(_make_app(
                user=User({'id': 1, 'permissions': ['SCHEDULE_READ']})))
            resp = client.get('/ris/resources/res-1/availability?date=2026-08-20')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['start'] == '08:00'
        called = engine.available_slots.await_args.kwargs
        assert called['resource_id'] == 'res-1'
        assert called['day'] == '2026-08-20'

    def test_availability_requires_date(self):
        client = TestClient(_make_app(
            user=User({'id': 1, 'permissions': ['SCHEDULE_READ']})))
        resp = client.get('/ris/resources/res-1/availability')
        assert resp.status_code == 422


class TestAppointments:
    def _app(self, perms):
        return _make_app(user=User({'id': 1, 'permissions': perms}))

    def test_list_appointments_requires_schedule_read(self):
        resp = TestClient(self._app([])).get('/ris/appointments')
        assert resp.status_code == 403

    def test_list_appointments_for_day(self):
        with patch('api.scheduling.get_conn') as conn_ctx, \
             patch('api.scheduling.RisAppointments') as repo_cls:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            repo = AsyncMock()
            repo.for_resource = AsyncMock(return_value=[
                {'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'},
            ])
            repo_cls.return_value = repo
            client = TestClient(self._app(['SCHEDULE_READ']))
            resp = client.get(
                '/ris/appointments?date=2026-08-20&resource_id=res-1')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['id'] == 'appt-1'

    def test_list_appointments_requires_date(self):
        resp = TestClient(self._app(['SCHEDULE_READ'])).get(
            '/ris/appointments')
        assert resp.status_code == 422

    def test_reschedule_requires_schedule_write(self):
        resp = TestClient(self._app([])).post(
            '/ris/appointments/appt-1/reschedule', json={})
        assert resp.status_code == 403

    def test_reschedule_calls_engine(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.reschedule = AsyncMock(return_value={
                'id': 'appt-1', 'start_time': '2026-08-20 10:00:00+00',
                'end_time': '2026-08-20 10:30:00+00'})
            engine_cls.return_value = engine
            client = TestClient(self._app(['SCHEDULE_WRITE']))
            resp = client.post('/ris/appointments/appt-1/reschedule', json={
                'new_start_time': '2026-08-20 10:00:00+00',
                'new_end_time': '2026-08-20 10:30:00+00',
                'reason': 'patient request'})
        assert resp.status_code == 200
        called = engine.reschedule.await_args.kwargs
        assert called['appointment_id'] == 'appt-1'

    def test_cancel_requires_schedule_write(self):
        resp = TestClient(self._app([])).post(
            '/ris/appointments/appt-1/cancel', json={})
        assert resp.status_code == 403

    def test_cancel_calls_engine(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.cancel = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'CANCELLED'})
            engine_cls.return_value = engine
            client = TestClient(self._app(['SCHEDULE_WRITE']))
            resp = client.post('/ris/appointments/appt-1/cancel', json={
                'reason': 'no-show'})
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'CANCELLED'
        called = engine.cancel.await_args.kwargs
        assert called['appointment_id'] == 'appt-1'
        assert called['reason'] == 'no-show'


    def test_create_appointment_requires_schedule_write(self):
        resp = TestClient(self._app([])).post('/ris/appointments', json={})
        assert resp.status_code == 403

    def test_create_appointment_calls_engine_book(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'SCHEDULED'})
            engine_cls.return_value = engine
            client = TestClient(self._app(['SCHEDULE_WRITE']))
            resp = client.post('/ris/appointments', json={
                'order_id': 'ord-1', 'resource_id': 'res-1',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00',
                'reason': 'routine', 'override_reason': 'urgent'})
        assert resp.status_code == 201
        called = engine.book.await_args.kwargs
        assert called['order_id'] == 'ord-1'
        assert called['override_reason'] == 'urgent'

    def test_create_appointment_without_override_reason(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'SCHEDULED'})
            engine_cls.return_value = engine
            client = TestClient(self._app(['SCHEDULE_WRITE']))
            resp = client.post('/ris/appointments', json={
                'order_id': 'ord-1', 'resource_id': 'res-1',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 201
        assert engine.book.await_args.kwargs['override_reason'] == ''


class TestResourceSchedules:
    def test_schedules_require_schedule_write(self):
        client = TestClient(_make_app(user=User({'id': 1, 'permissions': ['SCHEDULE_READ']})))
        resp = client.post('/ris/resources/res-1/schedules', json={
            'day_of_week': 1, 'start_time': '08:00:00', 'end_time': '17:00:00',
        })
        assert resp.status_code == 403

    def test_create_schedule_returns_201(self):
        with patch('api.scheduling.get_conn') as conn_ctx, \
             patch('api.scheduling.RisResourceSchedules') as repo:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            repo.return_value.create = AsyncMock(return_value={
                'id': 'sch-1', 'resource_id': 'res-1', 'tenant_id': 'default',
                'day_of_week': 1, 'start_time': '08:00:00', 'end_time': '17:00:00',
                'created_at': None,
            })
            client = TestClient(_make_app(
                user=User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
            resp = client.post('/ris/resources/res-1/schedules', json={
                'day_of_week': 1, 'start_time': '08:00:00', 'end_time': '17:00:00',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['day_of_week'] == 1

    def test_create_schedule_rejects_end_before_start(self):
        client = TestClient(_make_app(
            user=User({'id': 1, 'permissions': ['SCHEDULE_WRITE']})))
        resp = client.post('/ris/resources/res-1/schedules', json={
            'day_of_week': 1, 'start_time': '17:00:00', 'end_time': '08:00:00',
        })
        assert resp.status_code == 422