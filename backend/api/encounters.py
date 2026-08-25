"""RIS Encounters API (CS6/CC-03).

Patient-scoped contact log for the care coordinator. GET is patient-scoped
and gated by PATIENT_READ (chart browse); POST gates on ENCOUNTER_WRITE.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, validation_error
from api.validate import parse_body
from api.schemas.ris_encounters import EncounterRequest
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class EncounterHandler(HTTPEndpoint):
    """CS6: GET /ris/encounters?patient_id= and POST /ris/encounters."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        patient_id = request.query_params.get('patient_id', '')
        if not patient_id:
            return validation_error('patient_id is required')
        async with get_conn() as conn:
            from db.encounters import Encounters
            rows = await Encounters(conn).list(tenant, patient_id=patient_id)
        return ok({'data': rows})

    @requires_permission(Permission.ENCOUNTER_WRITE)
    async def post(self, request):
        body = await parse_body(EncounterRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.encounters import Encounters
            row = await Encounters(conn).create(
                patient_id=body.patient_id,
                encounter_type=body.encounter_type,
                summary=body.summary,
                occurred_at=body.occurred_at,
                linked_order_id=body.linked_order_id,
                linked_report_id=body.linked_report_id,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='encounter.recorded',
                actor_id=request.user.id,
                resource_type='encounters',
                resource_id=row['id'],
                tenant=tenant,
            )
        return created({'data': row})