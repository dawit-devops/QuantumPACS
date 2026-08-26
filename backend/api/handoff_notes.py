"""RIS Handoff Notes API (CC-08).

Coordinators leave handoff notes on patients visible to the next coordinator.
GET lists notes (per patient or all, with unread filter); POST creates a new
note; PATCH /{id}/read marks a note as read.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_handoff import CreateHandoffNoteRequest
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class HandoffNotesHandler(HTTPEndpoint):
    """CC-08: GET /ris/handoff-notes (list) and POST /ris/handoff-notes (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        patient_id = request.query_params.get('patient_id')
        unread_only = request.query_params.get('unread_only') == 'true'
        async with get_conn() as conn:
            from db.ris_handoff import HandoffNotes
            rows = await HandoffNotes(conn).list(
                tenant, patient_id=patient_id, unread_only=unread_only)
        return ok({'data': rows})

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateHandoffNoteRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_handoff import HandoffNotes
            row = await HandoffNotes(conn).create(
                patient_id=body.patient_id,
                note=body.note,
                priority=body.priority,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='handoff_note.created',
                actor_id=request.user.id,
                resource_type='ris_handoff_notes',
                resource_id=row['id'],
                details={'patient_id': body.patient_id, 'priority': body.priority},
                tenant=tenant,
            )
        return created({'data': row})


class HandoffNoteReadHandler(HTTPEndpoint):
    """CC-08: PATCH /ris/handoff-notes/{id}/read — mark as read."""

    @requires_permission(Permission.PATIENT_WRITE)
    async def patch(self, request):
        note_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_handoff import HandoffNotes
            hn = HandoffNotes(conn)
            existing = await hn.get(note_id, tenant)
            if not existing:
                return not_found('Handoff note not found')
            await hn.mark_read(note_id, tenant)
        return ok({'status': 'read'})