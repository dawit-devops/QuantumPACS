"""RIS Communication Log API (CS7/CC-04).

Inbound/outbound correspondence trail per patient. GET is patient-scoped
and gated by PATIENT_READ; POST (append-only log) gates on ENCOUNTER_WRITE.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, validation_error
from api.validate import parse_body
from api.schemas.ris_communications import CommunicationRequest
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class CommunicationHandler(HTTPEndpoint):
    """CS7: GET /ris/communications?patient_id= and POST /ris/communications."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        patient_id = request.query_params.get('patient_id', '')
        if not patient_id:
            return validation_error('patient_id is required')
        async with get_conn() as conn:
            from db.communications import Communications
            rows = await Communications(conn).list(
                tenant, patient_id=patient_id)
        return ok({'data': rows})

    @requires_permission(Permission.ENCOUNTER_WRITE)
    async def post(self, request):
        body = await parse_body(CommunicationRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.communications import Communications
            row = await Communications(conn).create(
                patient_id=body.patient_id,
                direction=body.direction,
                channel=body.channel,
                category=body.category,
                summary=body.summary,
                related_order_id=body.related_order_id,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='communication.logged',
                actor_id=request.user.id,
                resource_type='communications',
                resource_id=row['id'],
                tenant=tenant,
            )
        return created({'data': row})