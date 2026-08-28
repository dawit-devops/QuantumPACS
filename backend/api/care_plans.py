"""RIS Care Plans API (CS5/CC-02).

Care coordinators manage per-patient care plans (title, tasks, status,
provider, follow-up). GET is gated by PATIENT_READ (browse-access for
coordinator); POST and PATCH gate on CARE_PLAN_WRITE.
"""

from datetime import date, datetime, time
from uuid import UUID
import json

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_care_plans import CarePlanRequest
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


def _serialize(row):
    """DB row → JSON dict. asyncpg decodes jsonb to str by default, so the
    tasks list must be parsed here or the frontend renders/crashes on a
    string (CarePlans taskProgress calls .filter on it)."""
    d = dict(row)
    tasks = d.get('tasks')
    if isinstance(tasks, str):
        try:
            d['tasks'] = json.loads(tasks)
        except (ValueError, TypeError):
            d['tasks'] = []
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, UUID)):
            d[k] = str(v)
    return d


class CarePlanHandler(HTTPEndpoint):
    """CS5: GET /ris/care-plans (list) and POST /ris/care-plans (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            from db.care_plans import CarePlans
            rows = await CarePlans(conn).list(
                tenant, status=status, patient_id=patient_id)
        return ok({'data': rows})

    @requires_permission(Permission.CARE_PLAN_WRITE)
    async def post(self, request):
        body = await parse_body(CarePlanRequest, request)
        tenant = effective_tenant(request) or 'default'
        tasks = [m.model_dump() for m in (body.tasks or [])]
        async with get_conn() as conn:
            from db.care_plans import CarePlans
            row = await CarePlans(conn).create(
                patient_id=body.patient_id,
                title=body.title,
                tasks=tasks,
                responsible_provider=body.responsible_provider,
                follow_up_at=body.follow_up_at,
                notes=body.notes,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='care_plan.created',
                actor_id=request.user.id,
                resource_type='care_plans',
                resource_id=row['id'],
                tenant=tenant,
            )
        return created({'data': row})


class CarePlanDetailHandler(HTTPEndpoint):
    """CS5: PATCH /ris/care-plans/{id} — update status/tasks etc."""

    @requires_permission(Permission.CARE_PLAN_WRITE)
    async def patch(self, request):
        plan_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        body = await parse_body(CarePlanRequest, request)
        async with get_conn() as conn:
            from db.care_plans import CarePlans
            cp = CarePlans(conn)
            existing = await cp.get(plan_id, tenant)
            if not existing:
                return not_found('Care plan not found')
            tasks = [m.model_dump() for m in (body.tasks or [])]
            await cp.update(
                plan_id=plan_id,
                title=body.title,
                status=body.status,
                tasks=tasks,
                responsible_provider=body.responsible_provider,
                follow_up_at=body.follow_up_at,
                notes=body.notes,
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='care_plan.updated',
                actor_id=request.user.id,
                resource_type='care_plans',
                resource_id=plan_id,
                tenant=tenant,
            )
        return ok({'status': 'updated'})