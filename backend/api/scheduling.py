"""RIS scheduling API (S4-07) — resources + availability.

Resources are schedulable capacity (rooms, modalities, technologists)
with weekly availability windows (ris_resource_schedules). The booking
engine (S4-10) resolves conflicts against these; the calendar UI
(S4-08/S4-14) renders them. All endpoints gate on SCHEDULE_READ /
SCHEDULE_WRITE.
"""
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from config import config as _config

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import api_error, created, not_found, ok
from api.schemas.ris_scheduling import (
    CancelRequest, CreateAppointmentRequest, CreateResourceRequest,
    CreateScheduleRequest, RescheduleRequest,
)
from api.validate import parse_body
from api.tenant_middleware import effective_tenant
from db.conn import get_conn
from db.ris_appointments import RisAppointments
from db.ris_resources import RisResourceSchedules, RisResources
from services.scheduling.engine import (
    SchedulingConflict, SchedulingEngine, SchedulingNotFound,
    SchedulingValidation,
)


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
        # F-06: validate date format before it reaches the engine
        try:
            date.fromisoformat(day)
        except ValueError:
            return api_error('VALIDATION', f'Invalid date format: {day}', status=422)
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
        # F-06: validate date format before it reaches the engine
        try:
            day_parsed = date.fromisoformat(day)
        except ValueError:
            return api_error('VALIDATION', f'Invalid date format: {day}', status=422)
        # B-10: the day window must be interpreted in the clinic's
        # configured timezone — a naive UTC window shows a UTC+8 clinic
        # its slots on the wrong calendar day.
        tz = ZoneInfo(_config.get('clinic_timezone', 'UTC'))
        day_start = datetime.combine(day_parsed, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        async with get_conn() as conn:
            rows = await RisAppointments(conn).for_resource(
                params['resource_id'], day_start, day_end)
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateAppointmentRequest, request)
        # F-08: collapse whitespace-only override to '' so the engine rejects
        # a conflict instead of silently overriding with an empty audit reason.
        override_reason = (body.override_reason or '').strip()
        try:
            # H1: audit attribution — the engine's actor_id seeds created_by
            # and every APPOINTMENT_* audit event; it must be the real user.
            row = await SchedulingEngine(actor_id=request.user.id).book(
                order_id=body.order_id,
                patient_id=body.patient_id,
                resource_id=body.resource_id,
                start_time=body.start_time,
                end_time=body.end_time,
                reason=body.reason,
                override_reason=override_reason,
                prep_instructions=body.prep_instructions,
            )
        except SchedulingConflict as exc:
            # Overlap / prior-auth / outside-window rejections are expected
            # business outcomes, not server faults — the calendar must get a
            # 409 it can surface and refresh against (mirrors frontdesk.py).
            return api_error('SLOT_CONFLICT', str(exc), status=409)
        except SchedulingNotFound as exc:
            return not_found(str(exc))
        except SchedulingValidation as exc:
            return api_error('VALIDATION', str(exc), status=422)
        # R2-03-08: chargeback capture — record the requester's home site
        # so cross-facility activity is attributable even though the write
        # lands on the servicing site's data plane.
        home_tenant = getattr(request.user, 'tenant', '') or ''
        if home_tenant:
            async with get_conn() as conn:
                await RisAppointments(conn).stamp_requesting_tenant(
                    row['id'], home_tenant)
        return created({'data': _row_dict(row)})


class RisAppointmentRescheduleHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(RescheduleRequest, request)
        try:
            row = await SchedulingEngine(actor_id=request.user.id).reschedule(
                appointment_id=request.path_params['id'],
                new_start_time=body.new_start_time,
                new_end_time=body.new_end_time,
                reason=body.reason,
            )
        except SchedulingConflict as exc:
            return api_error('SLOT_CONFLICT', str(exc), status=409)
        except SchedulingNotFound as exc:
            return not_found(str(exc))
        except SchedulingValidation as exc:
            return api_error('VALIDATION', str(exc), status=422)
        return ok({'data': _row_dict(row)})


class RisAppointmentCancelHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CancelRequest, request)
        # H1: audit attribution on cancellation too.
        try:
            row = await SchedulingEngine(actor_id=request.user.id).cancel(
                appointment_id=request.path_params['id'],
                reason=body.reason,
            )
        except SchedulingNotFound as exc:
            return not_found(str(exc))
        return ok({'data': _row_dict(row)})

class MultiSiteAvailabilityHandler(HTTPEndpoint):
    """R2-03-05: GET /ris/scheduling/multisite-availability?date=YYYY-MM-DD

    One call, every accessible facility: the caller's home site plus any
    tenant they hold a user_tenant_grants row for. Sites without a
    registry row are skipped (revoked/decommissioned), and per-site data
    planes stay isolated — each section is read inside its own
    tenant_db_scope.
    """

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        from datetime import timedelta
        from zoneinfo import ZoneInfo
        from db.conn import get_tenant_slug
        from dcm.store import tenant_db_scope
        from db.user_tenant_grants import UserTenantGrants
        from db.tenants import Tenants

        day = request.query_params.get('date')
        if not day:
            return api_error('VALIDATION',
                             'date query parameter is required', status=422)
        try:
            day_parsed = date.fromisoformat(day)
        except ValueError:
            return api_error('VALIDATION', f'Invalid date format: {day}',
                             status=422)
        tz = ZoneInfo(_config.get('clinic_timezone', 'UTC'))
        day_start = datetime.combine(day_parsed, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)

        home = getattr(request.user, 'tenant', None) \
            or get_tenant_slug() or 'default'
        async with get_conn() as conn:
            grants = await UserTenantGrants(conn).list_for_user(
                str(getattr(request.user, 'id', '')))
            granted = [g['tenant_slug'] for g in grants]
            registry = Tenants(conn)

            sites = []
            seen = set()
            for slug in [home] + granted:
                if slug in seen:
                    continue
                seen.add(slug)
                info = await registry.get_by_slug(slug)
                if slug != home and not info:
                    continue  # revoked / decommissioned grant target
                resources_out = []
                scope_info = info or {}
                async with tenant_db_scope(slug, scope_info):
                    async with get_conn() as tconn:
                        res_rows = await RisResources(tconn).list_for_tenant()
                        appts = RisAppointments(tconn)
                        for r in res_rows:
                            booked = await appts.for_resource(
                                r['id'], day_start, day_end)
                            resources_out.append({
                                'resource': dict(r),
                                'booked': [_row_dict(a) for a in booked],
                            })
                sites.append({'site': slug, 'resources': resources_out})
        return ok({'data': {'date': day, 'sites': sites}})


class RisChargebackHandler(HTTPEndpoint):
    """R2-06-04: GET /ris/scheduling/chargeback?month=YYYY-MM-DD

    Servicing-site view of cross-facility activity: every booking this
    site performed for another site in the window, grouped by requester.
    Reconciliation input for inter-site billing.
    """

    @requires_permission(Permission.BILLING_READ)
    async def get(self, request):
        from datetime import timedelta

        raw = request.query_params.get('month')
        if raw:
            try:
                month_start = datetime.fromisoformat(raw)
            except ValueError:
                return api_error('VALIDATION',
                                 f'Invalid month: {raw}', status=422)
        else:
            today = date.today()
            month_start = datetime(today.year, today.month, 1)
        month_end = (month_start.replace(day=28) + timedelta(days=4))
        month_end = month_end.replace(day=1)

        async with get_conn() as conn:
            rows = await RisAppointments(conn).chargeback_summary(
                month_start=month_start, month_end=month_end,
                tenant_id=effective_tenant(request) or 'default')
        return ok({'data': [_row_dict(r) for r in rows]})
