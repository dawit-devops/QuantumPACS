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
from services.scheduling.engine import SchedulingConflict, SchedulingNotFound


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


class TestRequestHardening:
    """F-06/F-07/F-08 — input hardening for the scheduling API."""

    def _app(self, perms):
        return _make_app(user=User({'id': 1, 'permissions': perms}))

    def test_availability_rejects_malformed_date(self):
        # F-06 — a non-ISO date must be a 422 client error, not a 500.
        client = TestClient(self._app(['SCHEDULE_READ']))
        resp = client.get('/ris/resources/res-1/availability?date=Aug-20')
        assert resp.status_code == 422

    def test_list_appointments_rejects_malformed_date(self):
        client = TestClient(self._app(['SCHEDULE_READ']))
        resp = client.get('/ris/appointments?date=not-a-date&resource_id=res-1')
        assert resp.status_code == 422

    def test_create_appointment_rejects_overlong_fields(self):
        # F-07 — schema max_lengths keep a runaway caller out of the DB.
        client = TestClient(self._app(['SCHEDULE_WRITE']))
        resp = client.post('/ris/appointments', json={
            'order_id': 'ord-1', 'resource_id': 'res-1',
            'patient_id': 'X' * 200,
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00',
            'reason': 'r' * 5000,
        })
        assert resp.status_code == 422

    def test_override_reason_whitespace_only_is_treated_as_no_override(self):
        # F-08 — whitespace-only override must collapse to '' (no override),
        # so the engine rejects a conflict instead of silently overriding it.
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(side_effect=SchedulingConflict('busy'))
            engine_cls.return_value = engine
            client = TestClient(self._app(['SCHEDULE_WRITE']))
            resp = client.post('/ris/appointments', json={
                'order_id': 'ord-1', 'resource_id': 'res-1',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00',
                'override_reason': '   ',
            })
        assert resp.status_code == 409
        assert engine.book.await_args.kwargs['override_reason'] == ''

class TestAuditActorAttribution:
    """S4 (H1): audit events must carry the real user, not 'system'."""

    def _app(self, user):
        return _make_app(user=user)

    def test_book_passes_actor_id(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(return_value={'id': 'appt-1', 'status': 'SCHEDULED'})
            engine_cls.return_value = engine
            client = TestClient(self._app(User({
                'id': 42, 'permissions': ['SCHEDULE_WRITE'],
            })))
            resp = client.post('/ris/appointments', json={
                'order_id': 'ord-1', 'resource_id': 'res-1',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 201
        assert engine_cls.call_args.kwargs['actor_id'] == 42

    def test_reschedule_passes_actor_id(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.reschedule = AsyncMock(return_value={'id': 'appt-1'})
            engine_cls.return_value = engine
            client = TestClient(self._app(User({
                'id': 42, 'permissions': ['SCHEDULE_WRITE'],
            })))
            resp = client.post('/ris/appointments/appt-1/reschedule', json={
                'new_start_time': '2026-08-20 10:00:00+00',
                'new_end_time': '2026-08-20 10:30:00+00',
                'reason': 'patient request'})
        assert resp.status_code == 200
        assert engine_cls.call_args.kwargs['actor_id'] == 42

    def test_cancel_passes_actor_id(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.cancel = AsyncMock(return_value={'id': 'appt-1', 'status': 'CANCELLED'})
            engine_cls.return_value = engine
            client = TestClient(self._app(User({
                'id': 42, 'permissions': ['SCHEDULE_WRITE'],
            })))
            resp = client.post('/ris/appointments/appt-1/cancel', json={
                'reason': 'no-show'})
        assert resp.status_code == 200
        assert engine_cls.call_args.kwargs['actor_id'] == 42


class TestErrorContract:
    """S4 B-2/B-7/B-8: booking/reschedule/cancel must surface clean 4xx
    outcomes instead of 500s when inputs are malformed or reference
    missing entities — the calendar cannot recover from a server fault."""

    def _client(self):
        return TestClient(_make_app(User({
            'id': 42, 'permissions': ['SCHEDULE_WRITE'],
        })))

    def test_book_rejects_malformed_datetime(self):
        # B-8: 'garbage' must fail at the schema boundary (422), never
        # reach the engine.
        client = self._client()
        resp = client.post('/ris/appointments', json={
            'order_id': 'ord-1', 'resource_id': 'res-1',
            'patient_id': 'MRN-1',
            'start_time': 'garbage', 'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 422

    def test_book_rejects_empty_resource_id(self):
        # B-2: empty resource_id is unusable — 422 at the boundary.
        client = self._client()
        resp = client.post('/ris/appointments', json={
            'order_id': 'ord-1', 'resource_id': '',
            'patient_id': 'MRN-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 422

    def test_book_returns_404_when_order_missing(self):
        # B-7: a missing order is a not-found outcome, not a fault.
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(side_effect=SchedulingNotFound(
                'Order x not found for scheduling'))
            engine_cls.return_value = engine
            client = self._client()
            resp = client.post('/ris/appointments', json={
                'order_id': 'x', 'resource_id': 'res-1',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 404

    def test_book_returns_404_when_resource_missing(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.book = AsyncMock(side_effect=SchedulingNotFound(
                'Resource y not found'))
            engine_cls.return_value = engine
            client = self._client()
            resp = client.post('/ris/appointments', json={
                'order_id': '', 'resource_id': 'y',
                'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
        assert resp.status_code == 404

    def test_reschedule_returns_404_when_appointment_missing(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.reschedule = AsyncMock(side_effect=SchedulingNotFound(
                'Appointment z not found'))
            engine_cls.return_value = engine
            client = self._client()
            resp = client.post('/ris/appointments/z/reschedule', json={
                'new_start_time': '2026-08-20 10:00:00+00',
                'new_end_time': '2026-08-20 10:30:00+00',
                'reason': 'pt request'})
        assert resp.status_code == 404

    def test_cancel_returns_404_when_appointment_missing(self):
        with patch('api.scheduling.SchedulingEngine') as engine_cls:
            engine = AsyncMock()
            engine.cancel = AsyncMock(side_effect=SchedulingNotFound(
                'Appointment z not found'))
            engine_cls.return_value = engine
            client = self._client()
            resp = client.post('/ris/appointments/z/cancel', json={
                'reason': 'no-show'})
        assert resp.status_code == 404


class TestClinicDayWindow:
    """B-10: the appointments day listing must interpret the requested
    date in the clinic's configured timezone — a UTC-only window shows
    a UTC+8 clinic its slots on the wrong calendar day."""

    def test_list_appointments_uses_clinic_timezone_bounds(self):
        from unittest.mock import patch as _patch

        with _patch('api.scheduling._config') as cfg:
            cfg.get.return_value = 'Asia/Tokyo'
            user = User({'id': 1, 'permissions': ['SCHEDULE_READ']})
            client = TestClient(_make_app(user))
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.fetch.return_value = []
            with _patch('api.scheduling.get_conn', return_value=mock_conn):
                resp = client.get(
                    '/ris/appointments?date=2026-08-20&resource_id=res-1')
        assert resp.status_code == 200
        sql = str(mock_conn.fetch.call_args.args[0])
        # The day bounds must be tz-aware in the clinic zone (+09:00) —
        # a naive UTC window would render 'T00:00:00+00:00' and shift the
        # clinic's calendar day.
        assert "'2026-08-20T00:00:00+09:00'" in sql, sql
        assert "'2026-08-21T00:00:00+09:00'" in sql, sql
