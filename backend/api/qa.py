"""QA-09 Protocol Registry and QA-11 Corrective Actions endpoints."""

from datetime import datetime
from starlette.endpoints import HTTPEndpoint
from starlette.routing import Route

from api.rbac import requires_permission
from db.conn import get_conn
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_qa import (
    CreateProtocolRequest,
    UpdateProtocolRequest,
    CreateCorrectiveActionRequest,
    UpdateCorrectiveActionRequest,
)
from db.ris_protocols import RisProtocols
from db.ris_corrective_actions import RisCorrectiveActions
from api.permissions import Permission


def _row_dict(row):
    return dict(row) if row else None


# ── QA-09: Protocol Registry ────────────────────────────────────────
class ProtocolHandler(HTTPEndpoint):
    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        pid = request.path_params['id']
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            row = await repo.get(pid)
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.QA_WRITE)
    async def put(self, request):
        pid = request.path_params['id']
        body = await parse_body(UpdateProtocolRequest, request)
        data = body.model_dump(exclude_unset=True)
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            row = await repo.update(pid, data)
        if not row:
            return not_found('Protocol not found')
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.QA_WRITE)
    async def delete(self, request):
        pid = request.path_params['id']
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            await repo.delete(pid)
        return ok({'data': None})


class ProtocolListHandler(HTTPEndpoint):
    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        modality = request.query_params.get('modality')
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            if modality:
                rows = await repo.list_by_modality(modality)
            else:
                rows = await repo.list_all()
        return ok({'data': [dict(r) for r in rows]})

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        body = await parse_body(CreateProtocolRequest, request)
        data = body.model_dump()
        data['created_by'] = request.user.id
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            row = await repo.create(data)
        return created({'data': dict(row)})


class ProtocolDefaultHandler(HTTPEndpoint):
    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        pid = request.path_params['id']
        async with get_conn() as conn:
            repo = RisProtocols(conn)
            row = await repo.get(pid)
            if not row:
                return not_found('Protocol not found')
            row = await repo.set_default(pid, row['modality'])
        return ok({'data': _row_dict(row)})


# ── QA-11: Corrective Actions ──────────────────────────────────────
class CorrectiveActionHandler(HTTPEndpoint):
    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        aid = request.path_params['id']
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            row = await repo.get(aid)
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.QA_WRITE)
    async def put(self, request):
        aid = request.path_params['id']
        body = await parse_body(UpdateCorrectiveActionRequest, request)
        data = body.model_dump(exclude_unset=True)
        # Parse due_date string to datetime if provided
        if 'due_date' in data and data['due_date']:
            data['due_date'] = datetime.fromisoformat(data['due_date'])
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            row = await repo.update(aid, data)
        if not row:
            return not_found('Corrective action not found')
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.QA_WRITE)
    async def delete(self, request):
        aid = request.path_params['id']
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            await repo.delete(aid)
        return ok({'data': None})


class CorrectiveActionListHandler(HTTPEndpoint):
    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        view = request.query_params.get('view')  # 'overdue' for escalation
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            if view == 'overdue':
                rows = await repo.list_overdue()
            else:
                rows = await repo.list_all(status=status)
        return ok({'data': [dict(r) for r in rows]})

    @requires_permission(Permission.QA_WRITE)
    async def post(self, request):
        body = await parse_body(CreateCorrectiveActionRequest, request)
        data = body.model_dump()
        data['created_by'] = request.user.id
        if data.get('due_date'):
            data['due_date'] = datetime.fromisoformat(data['due_date'])
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            row = await repo.create(data)
        return created({'data': dict(row)})


# ── Escalation endpoint ────────────────────────────────────────────
class EscalationHandler(HTTPEndpoint):
    """QA-11: Scan for overdue actions and emit notifications."""
    @requires_permission(Permission.QA_READ)
    async def get(self, request):
        from api.notify import notify_role
        async with get_conn() as conn:
            repo = RisCorrectiveActions(conn)
            overdue = await repo.list_overdue()
            escalated = []
            for action in overdue:
                # Notify QA staff about overdue action
                await notify_role(
                    conn, 'qa',
                    'corrective_action.overdue',
                    'Overdue Corrective Action',
                    f'Action "{action["title"]}" is overdue '
                    f'(due: {action["due_date"]})',
                    f'/qa/corrective-actions/{action["id"]}',
                )
                escalated.append(str(action['id']))
        return ok({'data': {'escalated_count': len(escalated),
                            'escalated_ids': escalated}})


# ── Routes ─────────────────────────────────────────────────────────
routes = [
    Route('/ris/protocols', endpoint=ProtocolListHandler),
    Route('/ris/protocols/{id}', endpoint=ProtocolHandler),
    Route('/ris/protocols/{id}/default', endpoint=ProtocolDefaultHandler),
    Route('/ris/corrective-actions', endpoint=CorrectiveActionListHandler),
    # Static path BEFORE parameterised to avoid {id} matching 'escalate'.
    Route('/ris/corrective-actions/escalate', endpoint=EscalationHandler),
    Route('/ris/corrective-actions/{id}', endpoint=CorrectiveActionHandler),
]
