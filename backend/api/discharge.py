"""RIS Discharge Planning Checklist API (CC-06).

Coordinators create per-patient discharge checklists with template-based
items (follow-up, med reconciliation, patient education). GET lists
checklists (status/patient filters); POST creates a new checklist with
default items; PATCH /{id} updates status, items, and notes.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_discharge import (
    CreateDischargeChecklistRequest, UpdateDischargeChecklistRequest,
    DEFAULT_DISCHARGE_ITEMS,
)
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class DischargeChecklistsHandler(HTTPEndpoint):
    """CC-06: GET /ris/discharge-checklists (list) and POST (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            from db.ris_discharge import DischargeChecklists
            rows = await DischargeChecklists(conn).list(
                tenant, status=status, patient_id=patient_id)
        return ok({'data': rows})

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateDischargeChecklistRequest, request)
        tenant = effective_tenant(request) or 'default'
        if body.items:
            items = [m.model_dump() for m in body.items]
        else:
            items = DEFAULT_DISCHARGE_ITEMS
        async with get_conn() as conn:
            from db.ris_discharge import DischargeChecklists
            row = await DischargeChecklists(conn).create(
                patient_id=body.patient_id,
                title=body.title,
                items=items,
                notes=body.notes,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='discharge_checklist.created',
                actor_id=request.user.id,
                resource_type='ris_discharge_checklists',
                resource_id=row['id'],
                details={'patient_id': body.patient_id},
                tenant=tenant,
            )
        return created({'data': row})


class DischargeChecklistDetailHandler(HTTPEndpoint):
    """CC-06: PATCH /ris/discharge-checklists/{id} — update items, status."""

    @requires_permission(Permission.PATIENT_WRITE)
    async def patch(self, request):
        checklist_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        body = await parse_body(UpdateDischargeChecklistRequest, request)
        async with get_conn() as conn:
            from db.ris_discharge import DischargeChecklists
            dc = DischargeChecklists(conn)
            existing = await dc.get(checklist_id, tenant)
            if not existing:
                return not_found('Discharge checklist not found')
            items = [m.model_dump() for m in (body.items or [])]
            await dc.update(
                checklist_id=checklist_id,
                status=body.status,
                items=items,
                notes=body.notes,
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='discharge_checklist.updated',
                actor_id=request.user.id,
                resource_type='ris_discharge_checklists',
                resource_id=checklist_id,
                details={'status': body.status},
                tenant=tenant,
            )
        return ok({'status': 'updated'})