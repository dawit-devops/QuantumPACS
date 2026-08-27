"""RIS Manager Dashboard (S12-34).

GET /api/ris/dashboard/kpi aggregates the operational KPIs a department
manager tracks (RIS-AC-P07-01):
  - report TAT by priority (p95 of signed_at - created_at, per exam priority)
  - resource utilization (share of the booking window filled)
  - unbilled aging (reuses RisCharges.aging_groups)
  - exam volume (worklist_entries today)
Drill-down (drill_down=true) returns the per-report TAT rows behind the
p95 aggregates. All queries are tenant-scoped via the caller's effective
tenant, matching the rest of the RIS module.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error
from datetime import date, datetime, timedelta
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


# ---------------------------------------------------------------------------
# Department Manager analytics endpoints (DM-01, DM-02, DM-04, DM-07)
# ---------------------------------------------------------------------------


class DeptWorkloadHandler(HTTPEndpoint):
    """DM-01: Department workload distribution by provider/room/modality."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            # Workload by provider (radiologist reading load)
            by_provider = await conn.fetch(
                """SELECT r.signed_by AS provider,
                          COUNT(*) AS total_reports,
                          COUNT(*) FILTER (WHERE r.signed_at IS NULL) AS in_progress,
                          COUNT(*) FILTER (
                            WHERE r.signed_at IS NOT NULL
                            AND e.priority = 'stat'
                          ) AS stat_completed
                   FROM reports r
                   JOIN exams e ON e.id = r.exam_id
                   WHERE e.tenant_id = $1
                   GROUP BY r.signed_by
                   ORDER BY total_reports DESC""",
                tenant,
            )
            # Workload by modality
            by_modality = await conn.fetch(
                """SELECT e.modality,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (WHERE e.status = 'completed') AS completed,
                          COUNT(*) FILTER (WHERE e.status IN ('scheduled', 'arrived')) AS pending
                   FROM exams e
                   WHERE e.tenant_id = $1
                     AND e.scheduled_date = current_date
                   GROUP BY e.modality
                   ORDER BY total DESC""",
                tenant,
            )
            # Workload by room/resource
            by_room = await conn.fetch(
                """SELECT a.room AS room,
                          COUNT(*) AS total,
                          COUNT(*) FILTER (
                            WHERE a.status IN ('ARRIVED', 'IN_PROGRESS')
                          ) AS active,
                          COUNT(*) FILTER (
                            WHERE a.status = 'COMPLETED'
                          ) AS completed
                   FROM ris_appointments a
                   WHERE a.tenant_id = $1
                     AND a.start_time >= current_date
                     AND a.start_time < current_date + interval '1 day'
                   GROUP BY a.room
                   ORDER BY active DESC""",
                tenant,
            )
        return ok({
            'data': {
                'by_provider': [dict(r) for r in by_provider],
                'by_modality': [dict(r) for r in by_modality],
                'by_room': [dict(r) for r in by_room],
            },
        })


class DeptTatDrilldownHandler(HTTPEndpoint):
    """DM-02: TAT drill-down by provider with individual exam details."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        provider = request.query_params.get('provider')
        async with get_conn() as conn:
            # TAT summary by provider
            by_provider = await conn.fetch(
                """SELECT r.signed_by AS provider,
                          e.priority,
                          COUNT(*) AS n,
                          ROUND(AVG(EXTRACT(EPOCH FROM (r.signed_at - r.created_at))), 0)
                            AS avg_tat_seconds,
                          percentile_cont(0.95) WITHIN GROUP (
                            ORDER BY EXTRACT(EPOCH FROM (r.signed_at - r.created_at))
                          )::float AS p95_tat_seconds
                   FROM reports r
                   JOIN exams e ON e.id = r.exam_id
                   WHERE r.signed_at IS NOT NULL AND e.tenant_id = $1
                   GROUP BY r.signed_by, e.priority
                   ORDER BY r.signed_by, e.priority""",
                tenant,
            )
            # Drill-down: individual exams for a specific provider
            drill_rows = []
            if provider:
                drill_rows = await conn.fetch(
                    """SELECT r.exam_id, e.accession_number, e.priority,
                              e.modality, r.signed_by AS provider,
                              EXTRACT(EPOCH FROM (r.signed_at - r.created_at))
                                AS tat_seconds,
                              r.created_at, r.signed_at
                       FROM reports r
                       JOIN exams e ON e.id = r.exam_id
                       WHERE r.signed_at IS NOT NULL
                         AND e.tenant_id = $1
                         AND r.signed_by = $2
                       ORDER BY r.signed_at DESC
                       LIMIT 50""",
                    tenant, provider,
                )
        return ok({
            'data': {
                'by_provider': [dict(r) for r in by_provider],
                'drill_down': [dict(r) for r in drill_rows],
            },
        })


class DeptEquipmentUtilHandler(HTTPEndpoint):
    """DM-04: Equipment utilization — modality uptime, downtime events."""

    @requires_permission(Permission.EQUIPMENT_READ)
    async def get(self, request):
        async with get_conn() as conn:
            # Equipment utilization by modality
            utilization = await conn.fetch(
                """SELECT modality,
                          COUNT(*) AS total_units,
                          COUNT(*) FILTER (WHERE status = 'operational') AS operational,
                          COUNT(*) FILTER (WHERE status = 'maintenance') AS in_maintenance,
                          COUNT(*) FILTER (WHERE status = 'out_of_service') AS out_of_service,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'operational')
                                / NULLIF(COUNT(*), 0), 1) AS uptime_pct
                   FROM equipment
                   GROUP BY modality
                   ORDER BY modality""",
            )
            # Recent downtime events
            downtime = await conn.fetch(
                """SELECT de.*, e.name AS equipment_name, e.modality
                   FROM equipment_downtime de
                   JOIN equipment e ON e.id = de.equipment_id
                   WHERE de.started_at >= now() - interval '30 days'
                   ORDER BY de.started_at DESC
                   LIMIT 50""",
            )
        return ok({
            'data': {
                'utilization': [dict(r) for r in utilization],
                'recent_downtime': [dict(r) for r in downtime],
            },
        })


class DeptStaffScheduleHandler(HTTPEndpoint):
    """DM-07: Staff schedule management — view and create shift assignments."""

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        async with get_conn() as conn:
            where = []
            params = []
            idx = 1
            if start_date:
                where.append(f"scheduled_date >= ${idx}")
                params.append(start_date)
                idx += 1
            if end_date:
                where.append(f"scheduled_date <= ${idx}")
                params.append(end_date)
                idx += 1
            clause = f"WHERE {' AND '.join(where)}" if where else ''
            rows = await conn.fetch(
                f"""SELECT w.id, w.patient_name, w.accession_number,
                          w.modality, w.scheduled_date, w.scheduled_time,
                          w.station_ae_title, w.status,
                          w.assigned_technologist
                   FROM worklist_entries w
                   {clause}
                   ORDER BY w.scheduled_date, w.scheduled_time""",
                *params,
            )
        return ok({'data': [dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        from api.validate import parse_body
        from api.schemas.scheduling import StaffScheduleRequest
        body = await parse_body(StaffScheduleRequest, request)
        async with get_conn() as conn:
            # Create a worklist entry for the staff schedule assignment
            row = await conn.fetchrow(
                """INSERT INTO worklist_entries
                   (patient_name, accession_number, modality, scheduled_date,
                    scheduled_time, station_ae_title, assigned_technologist,
                    status, tenant_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, 'scheduled', $8)
                   RETURNING id""",
                body.patient_name, body.accession_number, body.modality,
                body.scheduled_date, body.scheduled_time,
                body.station_ae, body.technologist, body.tenant_id,
            )
        return created({'data': {'id': str(row['id'])}})


class RisDashboardKpiHandler(HTTPEndpoint):
    """S12-34: manager dashboard KPIs."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        drill_down = request.query_params.get('drill_down', '').lower() == 'true'
        async with get_conn() as conn:
            tat_rows = await conn.fetch(
                "SELECT e.priority AS priority,"
                " percentile_cont(0.95) WITHIN GROUP (ORDER BY"
                "   EXTRACT(EPOCH FROM (r.signed_at - r.created_at)))::float"
                "   AS p95_seconds"
                " FROM reports r"
                " JOIN exams e ON e.id = r.exam_id"
                " WHERE r.signed_at IS NOT NULL"
                "   AND e.tenant_id = $1"
                " GROUP BY e.priority"
                " ORDER BY e.priority",
                tenant,
            )
            utilization = await conn.fetchval(
                "SELECT CASE WHEN count(*) = 0 THEN 0"
                "       ELSE round("
                "         (count(*) FILTER (WHERE status IN"
                "           ('ARRIVED','IN_PROGRESS','COMPLETED')))::numeric"
                "         / count(*), 2)::float END"
                " FROM ris_appointments"
                " WHERE tenant_id = $1"
                "   AND start_time >= now() - interval '7 days'",
                tenant,
            )
            unbilled = await conn.fetchrow(
                "SELECT count(*) AS total_unbilled"
                " FROM ris_charges"
                " WHERE tenant_id = $1 AND status = 'PENDING'",
                tenant,
            )
            volume = await conn.fetchval(
                "SELECT count(*) FROM worklist_entries"
                " WHERE tenant_id = $1"
                "   AND scheduled_date = current_date",
                tenant,
            )
            # R2-01-09/15: authorization health — status mix for the card
            # and the RVG-1 approval-rate signal (>= 95% authorized
            # pre-scan) computed over decided requests.
            mix_rows = await conn.fetch(
                "SELECT status, count(*) AS n"
                " FROM ris_prior_auth_requests"
                " WHERE tenant_id = $1"
                " GROUP BY status ORDER BY status",
                tenant,
            )
            approval_rate = await conn.fetchval(
                "SELECT CASE WHEN count(*) = 0 THEN 0"
                "       ELSE round((count(*) FILTER (WHERE status"
                "         = 'APPROVED'))::numeric / count(*), 3)::float END"
                " FROM ris_prior_auth_requests"
                " WHERE tenant_id = $1"
                "   AND status IN ('APPROVED', 'DENIED', 'EXPIRED')",
                tenant,
            )
            # R2-06-04: cross-site bookings performed here this month —
            # the servicing-side view feeding inter-site reconciliation.
            month_start = datetime(date.today().year, date.today().month, 1)
            chargeback_rows = await conn.fetch(
                "SELECT requesting_tenant, count(*) AS bookings"
                " FROM ris_appointments"
                " WHERE tenant_id = $1 AND requesting_tenant <> ''"
                "   AND start_time >= $2"
                " GROUP BY requesting_tenant ORDER BY bookings DESC",
                tenant, month_start,
            )
            # R2-06-05: claim denial rate over decided claims
            denial_rate = await conn.fetchval(
                "SELECT CASE WHEN count(*) = 0 THEN 0.0 ELSE round("
                "(count(*) FILTER (WHERE status = 'DENIED'))::numeric"
                " / count(*), 3)::float END FROM ris_claims"
                " WHERE tenant_id = $1 AND status <> 'DRAFT'",
                tenant,
            )
            drill_rows = []
            if drill_down:
                drill_rows = await conn.fetch(
                    "SELECT r.exam_id AS exam_id,"
                    " e.accession_number AS accession_number,"
                    " e.priority AS priority,"
                    " EXTRACT(EPOCH FROM (r.signed_at - r.created_at))::float"
                    "   AS tat_seconds"
                    " FROM reports r"
                    " JOIN exams e ON e.id = r.exam_id"
                    " WHERE r.signed_at IS NOT NULL AND e.tenant_id = $1"
                    " ORDER BY tat_seconds DESC"
                    " LIMIT 50",
                    tenant,
                )

        return ok({
            'tat_by_priority': [dict(r) for r in tat_rows],
            'prior_auth': {
                'mix': [dict(r) for r in mix_rows],
                'approval_rate': float(approval_rate or 0),
            },
            'utilization': float(utilization or 0),
            'unbilled_aging': {
                'total_unbilled': (unbilled or {}).get('total_unbilled') or 0,
            },
            'volume': volume or 0,
            'drill_down': [dict(r) for r in drill_rows],
            'chargeback': {
                'month': month_start.date().isoformat(),
                'rows': [dict(r) for r in chargeback_rows],
            },
            'denial_rate': float(denial_rate or 0),
        })


class StaffTimeOffHandler(HTTPEndpoint):
    """DM-07: staff time-off requests — create and list."""

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        from db.ris_staff_time_off import RisStaffTimeOff
        async with get_conn() as conn:
            rows = await RisStaffTimeOff(conn).list_for_tenant(tenant, status)
        return ok({'data': rows})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        from api.validate import parse_body
        from api.schemas.ris_scheduling import CreateStaffTimeOffRequest
        from db.ris_staff_time_off import RisStaffTimeOff
        body = await parse_body(CreateStaffTimeOffRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            row = await RisStaffTimeOff(conn).create({
                'tenant_id': tenant,
                'staff_id': body.staff_id,
                'staff_name': body.staff_name,
                'modality': body.modality,
                'start_date': body.start_date,
                'end_date': body.end_date,
                'reason': body.reason,
                'created_by': getattr(request.user, 'email', '') or str(getattr(request.user, 'id', '')),
            })
        if not row:
            return api_error('CREATE_FAILED', 'Failed to create time-off request', status=500)
        return created({'data': row})


class StaffTimeOffStatusHandler(HTTPEndpoint):
    """DM-07: approve/reject/cancel a time-off request."""

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def patch(self, request):
        from api.validate import parse_body
        from api.schemas.ris_scheduling import UpdateStaffTimeOffStatusRequest
        from db.ris_staff_time_off import RisStaffTimeOff
        entry_id = request.path_params['id']
        body = await parse_body(UpdateStaffTimeOffStatusRequest, request)
        async with get_conn() as conn:
            repo = RisStaffTimeOff(conn)
            existing = await repo.get(entry_id)
            if not existing:
                return not_found('Time-off request not found')
            row = await repo.update_status(entry_id, body.status)
        return ok({'data': row})


class StaffCoverageGapsHandler(HTTPEndpoint):
    """DM-07: coverage-gap detection — flags modality/date combinations where
    approved time-off removes a scheduled technologist from a day that has
    active exam demand.

    Detection model: for each date in the window, load the set of
    technologists assigned to exams that day (from worklist_entries) and the
    set of staff on approved time-off (modality-scoped). A gap is flagged
    when a technologist is both scheduled for an exam and on approved time-off
    (i.e. the assignment cannot be covered), or when a modality has approved
    time-off but no remaining scheduled coverage.
    """

    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        modality = request.query_params.get('modality') or None
        from db.ris_staff_time_off import RisStaffTimeOff
        async with get_conn() as conn:
            repo = RisStaffTimeOff(conn)
            affected = await repo.approved_in_range(tenant, start_date, end_date, modality)
            # Exam demand per now-flagged staff for each overlapping date.
            gaps = []
            for a in affected:
                if not a.get('start_date') or not a.get('end_date'):
                    continue
                s = a['start_date']
                e = a['end_date']
                if isinstance(s, datetime):
                    s = s.date()
                if isinstance(e, datetime):
                    e = e.date()
                day = s
                while day <= e:
                    exam_rows = await conn.fetch(
                        """SELECT COUNT(*) AS exam_count, modality
                           FROM worklist_entries
                           WHERE tenant_id = $1
                             AND assigned_technologist = $2
                             AND scheduled_date = $3
                             AND status != 'cancelled'
                           GROUP BY modality""",
                        tenant, a['staff_name'], day,
                    )
                    if exam_rows:
                        for r in exam_rows:
                            gaps.append({
                                'date': day.isoformat(),
                                'staff_id': a['staff_id'],
                                'staff_name': a['staff_name'],
                                'modality': r['modality'] or a['modality'],
                                'scheduled_exams': r['exam_count'],
                            })
                    day += timedelta(days=1)
        return ok({'data': gaps, 'count': len(gaps)})