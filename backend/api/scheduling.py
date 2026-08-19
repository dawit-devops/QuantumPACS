"""RIS scheduling API (S4-07) — resources + availability.

Resources are schedulable capacity (rooms, modalities, technologists)
with weekly availability windows (ris_resource_schedules). The booking
engine (S4-10) resolves conflicts against these; the calendar UI
(S4-08/S4-14) renders them. All endpoints gate on SCHEDULE_READ /
SCHEDULE_WRITE.
"""
from datetime import date, datetime, time, timedelta
from uuid import UUID

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import api_error, created, ok
from api.schemas.ris_scheduling import (
    CancelRequest, CreateAppointmentRequest, CreateResourceRequest,
    CreateScheduleRequest, RescheduleRequest,
)
from api.validate import parse_body
from db.conn import get_conn
from db.ris_appointments import RisAppointments
from db.ris_resources import RisResourceSchedules, RisResources
from services.scheduling.engine import SchedulingEngine


def _row_dict(row):
    """Serialize a DB row for JSON responses — date/time/uuid become strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, UUID)):
            d[k] = str(v)
    return d


class RisResourcesHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateResourceRequest, request)
        async with get_conn() as conn:
            try:
                row = await RisResources(conn).create(body.model_dump())
            except Exception:
                from asyncpg import UniqueViolationError
                import sys
                if isinstance(sys.exc_info()[1], UniqueViolationError):
                    return api_error(
                        'CONFLICT',
                        f"Resource '{body.name}' already exists",
                        status=409,
                    )
                raise
        return created({'data': _row_dict(row)})

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        params = request.query_params
        async with get_conn() as conn:
            rows = await RisResources(conn).list_for_tenant(
                resource_type=params.get('resource_type') or None,
                modality=params.get('modality') or None,
            )
        return ok({'data': [_row_dict(r) for r in rows]})


class RisResourceSchedulesHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateScheduleRequest, request)
        async with get_conn() as conn:
            row = await RisResourceSchedules(conn).create({
                'resource_id': request.path_params['id'],
                **body.model_dump(),
            })
        return created({'data': _row_dict(row)})

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await RisResourceSchedules(conn).for_resource(
                request.path_params['id']
            )
        return ok({'data': [_row_dict(r) for r in rows]})


class RisResourceAvailabilityHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        day = request.query_params.get('date')
        if not day:
            return api_error('VALIDATION', 'date query parameter is required', status=422)
        slots = await SchedulingEngine().available_slots(
            resource_id=request.path_params['id'],
            day=day,
        )
        return ok({'data': slots})


class RisAppointmentsHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        params = request.query_params
        day = params.get('date')
        if not day:
            return api_error('VALIDATION', 'date query parameter is required', status=422)
        day_start = datetime.combine(
            date.fromisoformat(day), time.min).replace(tzinfo=None)
        day_end = day_start + timedelta(days=1)
        async with get_conn() as conn:
            rows = await RisAppointments(conn).for_resource(
                params['resource_id'], day_start, day_end)
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateAppointmentRequest, request)
        row = await SchedulingEngine().book(
            order_id=body.order_id,
            patient_id=body.patient_id,
            resource_id=body.resource_id,
            start_time=body.start_time,
            end_time=body.end_time,
            reason=body.reason,
            override_reason=body.override_reason,
        )
        return created({'data': _row_dict(row)})


class RisAppointmentRescheduleHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(RescheduleRequest, request)
        row = await SchedulingEngine().reschedule(
            appointment_id=request.path_params['id'],
            new_start_time=body.new_start_time,
            new_end_time=body.new_end_time,
            reason=body.reason,
        )
        return ok({'data': _row_dict(row)})


class RisAppointmentCancelHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CancelRequest, request)
        row = await SchedulingEngine().cancel(
            appointment_id=request.path_params['id'],
            reason=body.reason,
        )
        return ok({'data': _row_dict(row)})