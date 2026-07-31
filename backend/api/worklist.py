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
from log import request_id_var


class WorklistHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        modality = request.query_params.get('modality')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')
        page = int(request.query_params.get('page', '1'))
        per_page = int(request.query_params.get('per_page', '20'))

        async with get_conn() as conn:
            entries, total = await Worklist(conn).search(
                status=status, modality=modality,
                date_from=date_from, date_to=date_to,
                search=search, page=page, per_page=per_page,
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
                tenant=request.user.tenant,
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

class WorklistStationAeHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        async with get_conn() as conn:
            stations = await Worklist(conn).get_station_aes()
        return ok(stations)
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
                tenant=request.user.tenant,
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
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({})
