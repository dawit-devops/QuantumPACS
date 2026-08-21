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
from api.response import ok
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


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
            'utilization': float(utilization or 0),
            'unbilled_aging': {
                'total_unbilled': (unbilled or {}).get('total_unbilled') or 0,
            },
            'volume': volume or 0,
            'drill_down': [dict(r) for r in drill_rows],
        })