"""Modality Worklist (MWL) endpoints for DICOM scheduled procedure management —
CRUD operations on worklist entries with HL7-compatible field mappings
and audit logging for each state transition."""
from datetime import datetime, timezone

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import not_found, ok, created
from api.validate import parse_body
from api.schemas.worklist import CreateWorklistRequest, UpdateWorklistRequest
from db.audit_log import AuditLog
from db.conn import get_conn
from db.worklist import Worklist
from log import request_id_var, get_logger
from api.tenant_middleware import effective_tenant
from api.mwl_sync import MwlSyncer

log = get_logger(__name__)


class WorklistHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        modality = request.query_params.get('modality')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')
        # F-01: clamp page/per_page like sibling endpoints — an unbounded
        # per_page lets any WORKLIST_READ holder dump the entire tenant PHI
        # schedule in one call (CWE-770/CWE-200).
        try:
            page = max(1, int(request.query_params.get('page', '1')))
            per_page = min(200, max(1, int(request.query_params.get('per_page', '20'))))
        except (TypeError, ValueError):
            from api.response import validation_error
            return validation_error('Invalid pagination parameters')

        async with get_conn() as conn:
            entries, total = await Worklist(conn).search(
                status=status, modality=modality,
                date_from=date_from, date_to=date_to,
                search=search, page=page, per_page=per_page,
                # F2: row-level tenant scope — shared-DB tenants share one
                # table, so pool isolation alone leaks other tenants' PHI.
                tenant_id=effective_tenant(request) or 'default',
            )
        return ok({'data': entries, 'total': total, 'page': page, 'per_page': per_page})

    @requires_permission(Permission.WORKLIST_WRITE)
    async def post(self, request):
        body = await parse_body(CreateWorklistRequest, request)
        async with get_conn() as conn:
            entry = await Worklist(conn).create({
                'patient_id': body.patient_id,
                'patient_name': body.patient_name,
                'patient_birth_date': body.patient_birth_date,
                'patient_sex': body.patient_sex,
                'accession_number': body.accession_number,
                'requested_procedure_id': body.requested_procedure_id,
                'requested_procedure_desc': body.requested_procedure_desc,
                'scheduled_procedure_step_id': body.scheduled_procedure_step_id,
                'protocol_name': body.protocol_name,
                'requesting_physician': body.requesting_physician,
                'scheduled_date': body.scheduled_date,
                'scheduled_time': body.scheduled_time,
                'modality': body.modality,
                'station_ae_title': body.station_ae_title,
                'status': 'scheduled',
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='worklist.entry_created',
                actor_id=request.user.id,
                resource_type='worklist_entry',
                resource_id=entry['id'],
                details={
                    'patient_id': body.patient_id,
                    'accession_number': body.accession_number,
                    'modality': body.modality,
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': entry})


class WorklistEntryHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        entry_id = request.path_params['id']
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM worklist_entries WHERE id = $1",
                entry_id,
            )
        if not row:
            return not_found('Worklist entry not found')
        return ok({'data': dict(row)})

    @requires_permission(Permission.WORKLIST_WRITE)
    async def put(self, request):
        entry_id = request.path_params['id']
        body = await parse_body(UpdateWorklistRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await conn.fetchval(
                "SELECT id FROM worklist_entries WHERE id = $1",
                entry_id,
            )
            if not existing:
                return not_found('Worklist entry not found')
            now = datetime.now(timezone.utc)
            keys = list(updates.keys()) + ['updated_at']
            values = list(updates.values()) + [now]
            set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
            await conn.execute(
                f"UPDATE worklist_entries SET {set_clause} WHERE id = $1",
                entry_id, *values,
            )
            await AuditLog(conn).log_event(
                event_type='worklist.entry_updated',
                actor_id=request.user.id,
                resource_type='worklist_entry',
                resource_id=entry_id,
                details=updates,
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})

    @requires_permission(Permission.WORKLIST_WRITE)
    async def delete(self, request):
        entry_id = request.path_params['id']
        async with get_conn() as conn:
            await Worklist(conn).cancel(entry_id)
            await AuditLog(conn).log_event(
                event_type='worklist.entry_cancelled',
                actor_id=request.user.id,
                resource_type='worklist_entry',
                resource_id=entry_id,
                details={},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class WorklistStationAeHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        async with get_conn() as conn:
            stations = await Worklist(conn).get_station_aes()
        return ok(stations)


# ---------------------------------------------------------------------------
# S6-13: Tracking Board API
# ---------------------------------------------------------------------------

# M-10: single source of truth for tracking transitions — the board map
# lives once below (TRACKING_VALID_TRANSITIONS); a second copy here was a
# drift hazard (a map duplicated twice WILL diverge).


class TrackingHandler(HTTPEndpoint):
    """S6-13: Live tracking board — joins worklist entries with exams."""

    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        status = request.query_params.get('status')
        priority = request.query_params.get('priority')
        search = request.query_params.get('search')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        try:
            page = max(1, int(request.query_params.get('page', '1')))
            per_page = min(200, max(1, int(request.query_params.get('per_page', '20'))))
        except (TypeError, ValueError):
            from api.response import validation_error
            return validation_error('Invalid pagination parameters')

        conditions = []
        params = []
        idx = 1
        # F2: row-level tenant scope for the tracking board (same surface
        # family as the worklist — shared-DB tenants share one table).
        conditions.append(f'w.tenant_id = ${idx}')
        params.append(effective_tenant(request) or 'default')
        idx += 1
        if modality:
            conditions.append(f'w.modality = ${idx}')
            params.append(modality)
            idx += 1
        if status:
            conditions.append(f'w.status = ${idx}')
            params.append(status)
            idx += 1
        if priority:
            conditions.append(f'w.requested_procedure_priority = ${idx}')
            params.append(priority)
            idx += 1
        if search:
            # S-6: user input must not act as LIKE syntax — '100%' is a
            # literal percent in a patient search, not a wildcard. Escape
            # the wildcard characters and declare ESCAPE on the ILIKE.
            escaped = (
                search.replace('\\', '\\\\')
                      .replace('%', '\\%')
                      .replace('_', '\\_')
            )
            conditions.append(
                f'(w.patient_name ILIKE ${idx} ESCAPE \'\\\' '
                f'OR w.patient_id ILIKE ${idx} ESCAPE \'\\\' '
                f'OR w.accession_number ILIKE ${idx} ESCAPE \'\\\')'
            )
            params.append(f'%{escaped}%')
            idx += 1
        if date_from:
            conditions.append(f'w.scheduled_date >= ${idx}')
            params.append(date_from)
            idx += 1
        if date_to:
            conditions.append(f'w.scheduled_date <= ${idx}')
            params.append(date_to)
            idx += 1

        where = ' AND '.join(conditions) if conditions else '1=1'

        async with get_conn() as conn:
            rows = await conn.fetch(
                f"SELECT w.*, e.status AS exam_status, e.priority AS exam_priority,"
                f" e.assigned_technologist, e.protocol_name AS exam_protocol,"
                f" (EXISTS (SELECT 1 FROM ris_critical_results cr"
                f"   WHERE cr.accession_number = w.accession_number"
                f"   AND cr.status = 'flagged')) AS has_critical,"
                f" appt.id AS appointment_id, appt.resource_id AS resource_id,"
                f" appt.checked_in_at AS checked_in_at"
                f" FROM worklist_entries w"
                f" LEFT JOIN exams e ON e.accession_number = w.accession_number"
                f" LEFT JOIN LATERAL (SELECT a.id, a.resource_id, a.checked_in_at"
                f"   FROM ris_appointments a"
                f"   WHERE a.order_id = w.ris_order_id"
                f"     AND a.status IN ('SCHEDULED', 'ARRIVED')"
                f"   ORDER BY a.start_time LIMIT 1) appt ON true"
                f" WHERE {where}"
                f" ORDER BY"
                f" CASE WHEN w.requested_procedure_priority IN ('STAT','S') THEN 0"
                f"      WHEN w.requested_procedure_priority IN ('A','ASAP','U','URGENT') THEN 1"
                f"      ELSE 3 END,"
                f" w.scheduled_date DESC, w.scheduled_time DESC"
                f" LIMIT ${idx} OFFSET ${idx + 1}",
                *params, per_page, (page - 1) * per_page,
            )
            total = await conn.fetchval(
                f"SELECT count(*) FROM worklist_entries w"
                f" WHERE {where}",
                *params,
            )

        now = datetime.now(timezone.utc)
        data = []
        for r in rows:
            row = dict(r)
            # FD-05: minutes-since-arrival so the queue can color-code by
            # wait time. None when the appointment has no arrival stamp.
            ck = row.get('checked_in_at')
            if ck is not None:
                if isinstance(ck, str):
                    ck = datetime.fromisoformat(ck)
                row['wait_minutes'] = max(
                    0, int((now - ck).total_seconds() // 60))
            else:
                row['wait_minutes'] = None
            data.append(row)

        return ok({
            'data': data,
            'total': total or 0,
            'page': page,
            'per_page': per_page,
        })


class TrackingKpiHandler(HTTPEndpoint):
    """S6-14: KPI strip — live counts for today's exams."""

    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        # F2: KPI counts must match the board's tenant scope — otherwise the
        # strip counts other tenants' rows (acme showed Overdue=318 from
        # perf-*/e2e-* slugs while its own board was empty).
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            volume = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE scheduled_date = current_date AND tenant_id = $1",
                tenant,
            ) or 0
            in_progress = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE status = 'in_progress'"
                " AND scheduled_date = current_date AND tenant_id = $1",
                tenant,
            ) or 0
            awaiting_read = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE status = 'performed'"
                " AND scheduled_date = current_date AND tenant_id = $1",
                tenant,
            ) or 0
            overdue = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE status = 'scheduled'"
                " AND scheduled_date < current_date AND tenant_id = $1",
                tenant,
            ) or 0
            stat_count = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE requested_procedure_priority IN ('STAT','S')"
                " AND scheduled_date = current_date AND tenant_id = $1"
                " AND status NOT IN ('cancelled','performed')",
                tenant,
            ) or 0
            # FD-05: patients waiting >30 minutes in the queue.
            overdue_wait = await conn.fetchval(
                "SELECT count(*) FROM ris_appointments"
                " WHERE status = 'ARRIVED'"
                " AND checked_in_at < now() - interval '30 minutes'"
                " AND start_time >= date_trunc('day', now())"
                " AND tenant_id = $1",
                tenant,
            ) or 0

        return ok({
            'volume': volume,
            'in_progress': in_progress,
            'awaiting_read': awaiting_read,
            'overdue': overdue,
            'stat_count': stat_count,
            'overdue_wait_count': overdue_wait,
        })


class TrackingTimelineHandler(HTTPEndpoint):
    """S6-16: Status timeline — ordered status changes for an exam."""

    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        exam_id = request.path_params['id']
        async with get_conn() as conn:
            rows = await conn.fetch(
                "SELECT (l.log::json->>'event') AS event_type,"
                " (l.log::json->>'actor') AS actor_id,"
                " (l.log::json->>'detail') AS details,"
                " l.created AS created_at"
                " FROM logs l"
                " WHERE (l.log::json->'resource'->>'type') = 'worklist_entry'"
                " AND (l.log::json->'resource'->>'id') = $1"
                " ORDER BY l.created ASC",
                exam_id,
            )
        return ok({'data': [dict(r) for r in rows]})


# M-10: the canonical tracking transition map (deduplicated).
TRACKING_VALID_TRANSITIONS = {
    'scheduled': {'arrived', 'cancelled'},
    'arrived': {'in_progress', 'cancelled'},
    'in_progress': {'completed', 'cancelled'},
    'completed': set(),
    'cancelled': set(),
}


class TrackingStatusHandler(HTTPEndpoint):
    """S6-15: Manual status update with guard validation."""

    @requires_permission(Permission.WORKLIST_WRITE)
    async def put(self, request):
        from api.validate import parse_body
        from pydantic import BaseModel

        class StatusUpdate(BaseModel):
            status: str

        body = await parse_body(StatusUpdate, request)
        new_status = body.status
        entry_id = request.path_params['id']

        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT id, status FROM worklist_entries WHERE id = $1",
                entry_id,
            )
            if not row:
                return not_found('Entry not found')

            current = row['status']
            allowed = TRACKING_VALID_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                from api.response import api_error
                return api_error(
                    'VALIDATION',
                    f'Cannot transition from {current} to {new_status}',
                    status=409,
                )

            # S6-24: the guarded UPDATE is the race backstop — two concurrent
            # PUTs that both passed the pre-check cannot both win; the loser
            # gets a 409 instead of overwriting the winner's status.
            from db.worklist import Worklist
            applied = await Worklist(conn).update_status_if(
                entry_id, current, new_status)
            if not applied:
                from api.response import api_error
                return api_error(
                    'VALIDATION',
                    f'Entry already transitioned from {current}',
                    status=409,
                )

            await AuditLog(conn).log_event(
                event_type='worklist.status_updated',
                actor_id=request.user.id,
                resource_type='worklist_entry',
                resource_id=entry_id,
                details={'from': current, 'to': new_status},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )

        return ok({'data': {'status': new_status}})


class WorklistSyncHandler(HTTPEndpoint):
    """T-05: manual MWL sync trigger — POST /worklist/sync.

    Replays dirty entries to the DICOM archive via MwlSyncer.run_once() and
    returns the outcome counts so the UI can render a "MWL Synced ✓ /
    Pending ⏳" status with a last-sync time. Gated WORKLIST_WRITE."""

    @requires_permission(Permission.WORKLIST_WRITE)
    async def post(self, request):
        try:
            stats = await MwlSyncer().run_once()
        except Exception as e:  # sync worker failure — surface, don't 500-crash
            from api.response import api_error
            log.warning('Manual MWL sync failed: %s', e)
            return api_error('SYNC_FAILED', 'MWL sync failed', status=500)
        if stats is None:
            # DICOM proxy disabled — nothing to sync to.
            return ok({'data': {'synced': False, 'reason': 'disabled'}})
        return ok({'data': {**stats, 'synced': True}})
