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
    ApplyTemplateRequest, CancelRequest, CreateAppointmentRequest,
    BatchBookAppointmentRequest,
    CreateResourceRequest, CreateScheduleRequest, CreateTemplateRequest,
    RescheduleRequest,
)
from api.validate import parse_body
from api.tenant_middleware import effective_tenant
from db.conn import get_conn
from db.audit_log import AuditLog
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
        tz = ZoneInfo(_config.get('clinic_timezone', 'UTC'))
        # S-03: support both single-day (date) and range (date_from/date_to)
        # queries. Range mode returns all appointments across all resources
        # for the week/month calendar views.
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        day = params.get('date')
        resource_id = params.get('resource_id')

        if date_from and date_to:
            # Range mode (S-03 week/month views)
            try:
                from_parsed = date.fromisoformat(date_from)
                to_parsed = date.fromisoformat(date_to)
            except ValueError:
                return api_error('VALIDATION',
                                 'Invalid date format', status=422)
            range_start = datetime.combine(from_parsed, time.min, tzinfo=tz)
            range_end = datetime.combine(to_parsed + timedelta(days=1),
                                         time.min, tzinfo=tz)
            async with get_conn() as conn:
                repo = RisAppointments(conn)
                if resource_id:
                    rows = await repo.for_resource(
                        resource_id, range_start, range_end)
                else:
                    rows = await repo.for_date_range(
                        range_start, range_end)
            return ok({'data': [_row_dict(r) for r in rows]})

        # Single-day mode (existing behavior)
        if not day:
            return api_error('VALIDATION',
                             'date query parameter is required', status=422)
        # F-06: validate date format before it reaches the engine
        try:
            day_parsed = date.fromisoformat(day)
        except ValueError:
            return api_error('VALIDATION', f'Invalid date format: {day}', status=422)
        # B-10: the day window must be interpreted in the clinic's
        # configured timezone — a naive UTC window shows a UTC+8 clinic
        # its slots on the wrong calendar day.
        day_start = datetime.combine(day_parsed, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        async with get_conn() as conn:
            repo = RisAppointments(conn)
            if resource_id:
                rows = await repo.for_resource(
                    resource_id, day_start, day_end)
            else:
                # FD-06: no resource_id → cross-resource "today" aggregate
                # for the front-desk schedule, with modality/status filters.
                rows = await repo.for_day(
                    day_start, day_end,
                    modality=params.get('modality') or '',
                    status=params.get('status') or '',
                )
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


class RisBatchAppointmentsHandler(HTTPEndpoint):
    """S-06: batch booking — POST /ris/appointments/batch.

    Books several appointments in one call (e.g. "book 3 CT slots"). Each
    item is a full single-booking payload; bookings are attempted
    independently so one conflict reports that item as failed without
    rolling back the rest. The response carries a per-item result list the
    UI can surface ("3 of 5 booked; 2 conflicts").
    """

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(BatchBookAppointmentRequest, request)
        results = []
        for b in body.bookings:
            override_reason = (b.override_reason or '').strip()
            try:
                row = await SchedulingEngine(actor_id=request.user.id).book(
                    order_id=b.order_id,
                    patient_id=b.patient_id,
                    resource_id=b.resource_id,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    reason=b.reason,
                    override_reason=override_reason,
                    prep_instructions=b.prep_instructions,
                )
                results.append({'success': True, 'appointment': _row_dict(row)})
            except SchedulingConflict as exc:
                results.append({'success': False, 'code': 'SLOT_CONFLICT',
                                'message': str(exc)})
            except SchedulingNotFound as exc:
                results.append({'success': False, 'code': 'NOT_FOUND',
                                'message': str(exc)})
            except SchedulingValidation as exc:
                results.append({'success': False, 'code': 'VALIDATION',
                                'message': str(exc)})
        # R2-03-08: chargeback capture for the items that landed.
        home_tenant = getattr(request.user, 'tenant', '') or ''
        if home_tenant:
            async with get_conn() as conn:
                for res in results:
                    if res['success']:
                        await RisAppointments(conn).stamp_requesting_tenant(
                            res['appointment']['id'], home_tenant)
        return created({'data': {'results': results}})


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


class RisAppointmentCheckInHandler(HTTPEndpoint):
    """FD-04: staff one-click check-in — POST /ris/appointments/{id}/check-in.

    The kiosk (PortalCheckInHandler) flips SCHEDULED -> ARRIVED with the
    HMAC token as the bearer credential. Front-desk staff need the same
    transition from an authenticated session: gated SCHEDULE_WRITE (held by
    receptionists), audited ris.checkin_staff with the real actor. The
    transition is idempotent for an already-ARRIVED appointment.
    """

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        appointment_id = request.path_params['id']
        async with get_conn() as conn:
            repo = RisAppointments(conn)
            current = await repo.get(appointment_id)
            if current is None:
                return not_found('Appointment not found')
            if current['status'] == 'ARRIVED':
                # Idempotent: an already-arrived appointment is a no-op — no
                # state flip, but the staff click is still auditable.
                await AuditLog(conn).log_event(
                    event_type='ris.checkin_staff',
                    actor_id=request.user.id,
                    resource_id=appointment_id,
                    resource_type='ris_appointments',
                    tenant=effective_tenant(request) or 'default',
                )
                return ok({'data': _row_dict(current)})
            if current['status'] != 'SCHEDULED':
                return api_error('STATE_CONFLICT',
                                 f'Cannot check in appointment in '
                                 f'{current["status"]} state', status=409)
            row = await repo.mark_checked_in(appointment_id)
            if row is None:
                return api_error('STATE_CONFLICT',
                                 'Appointment not in SCHEDULED state',
                                 status=409)
            await AuditLog(conn).log_event(
                event_type='ris.checkin_staff',
                actor_id=request.user.id,
                resource_id=appointment_id,
                resource_type='ris_appointments',
                tenant=effective_tenant(request) or 'default',
            )
        return ok({'data': _row_dict(row)})


class RisScheduleTemplatesHandler(HTTPEndpoint):
    """S-05: schedule templates — list (GET) + create (POST).

    Templates are named sets of weekly windows that can be applied to any
    resource. Gated SCHEDULE_READ (list) / SCHEDULE_WRITE (create).
    """

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        from db.ris_schedule_templates import RisScheduleTemplates
        async with get_conn() as conn:
            rows = await RisScheduleTemplates(conn).list_for_tenant()
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        from db.ris_schedule_templates import RisScheduleTemplates
        body = await parse_body(CreateTemplateRequest, request)
        async with get_conn() as conn:
            row = await RisScheduleTemplates(conn).create({
                'name': body.name,
                'slots': [s.model_dump() for s in body.slots],
                'created_by': str(request.user.id),
            })
        return created({'data': _row_dict(row)})


class RisScheduleTemplateApplyHandler(HTTPEndpoint):
    """S-05: apply a template to a resource — batch-create schedules.

    POST /ris/schedule-templates/{id}/apply {resource_id: '...'}
    Reads the template's slots, deletes existing schedules for the
    resource (clean slate), then batch-inserts new ris_resource_schedules.
    Gated SCHEDULE_WRITE.
    """

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        from db.ris_schedule_templates import RisScheduleTemplates
        body = await parse_body(ApplyTemplateRequest, request)
        template_id = request.path_params['id']
        async with get_conn() as conn:
            tpl = await RisScheduleTemplates(conn).get(template_id)
            if tpl is None:
                return not_found(f'Template {template_id} not found')
            # Clean slate: remove existing schedules for the target resource.
            existing = await RisResourceSchedules(conn).for_resource(
                body.resource_id)
            for s in existing:
                await RisResourceSchedules(conn).delete(s['id'])
            # Batch-insert template slots as new schedules.
            created_count = 0
            for slot in (tpl.get('slots') or []):
                await RisResourceSchedules(conn).create({
                    'resource_id': body.resource_id,
                    'day_of_week': slot['day_of_week'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                })
                created_count += 1
        return ok({'data': {'created': created_count}})


class RisAppointmentNoShowHandler(HTTPEndpoint):
    """S-13: mark appointment as no-show — POST /ris/appointments/{id}/no-show.

    Flips SCHEDULED/ARRIVED -> NO_SHOW via RisAppointments.mark_no_show,
    gated SCHEDULE_WRITE, audited ris.no_show. Only valid from SCHEDULED
    or ARRIVED (terminal states like COMPLETED/CANCELLED reject with 409).
    Idempotent for already-NO_SHOW.
    """

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        appointment_id = request.path_params['id']
        async with get_conn() as conn:
            repo = RisAppointments(conn)
            current = await repo.get(appointment_id)
            if current is None:
                return not_found('Appointment not found')
            if current['status'] == 'NO_SHOW':
                # Idempotent: already marked no-show is a no-op.
                await AuditLog(conn).log_event(
                    event_type='ris.no_show',
                    actor_id=request.user.id,
                    resource_id=appointment_id,
                    resource_type='ris_appointments',
                    tenant=effective_tenant(request) or 'default',
                )
                return ok({'data': _row_dict(current)})
            if current['status'] not in ('SCHEDULED', 'ARRIVED'):
                return api_error('STATE_CONFLICT',
                                 f'Cannot mark no-show in '
                                 f'{current["status"]} state', status=409)
            row = await repo.mark_no_show(appointment_id)
            if row is None:
                return api_error('STATE_CONFLICT',
                                 'Appointment not in SCHEDULED/ARRIVED state',
                                 status=409)
            await AuditLog(conn).log_event(
                event_type='ris.no_show',
                actor_id=request.user.id,
                resource_id=appointment_id,
                resource_type='ris_appointments',
                tenant=effective_tenant(request) or 'default',
            )
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
