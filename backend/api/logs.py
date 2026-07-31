from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, forbidden
from db.conn import get_conn
from db.audit_log import AuditLog


class LogsHandler(HTTPEndpoint):
    @requires_permission(Permission.LOG_READ)
    async def get(self, request):
        event_type = request.query_params.get('event_type')
        actor = request.query_params.get('actor')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        tenant_filter = request.query_params.get('tenant')
        cursor = request.query_params.get('cursor')
        limit = int(request.query_params.get('limit', 50))
        limit = max(10, min(200, limit))

        if event_type:
            event_type = event_type.split(',')

        user = request.user
        perms = getattr(user, 'permissions', [])

        tenant = getattr(user, 'tenant', None)
        if tenant_filter:
            if Permission.TENANT_READ.value not in perms:
                return forbidden('Missing permission: TENANT_READ')
            tenant = tenant_filter

        async with get_conn() as conn:
            audit = AuditLog(conn)
            data = await audit.query(
                event_type=event_type,
                actor=actor,
                date_from=date_from,
                date_to=date_to,
                tenant=tenant,
                cursor=cursor,
                limit=limit,
            )
            total = await audit.count(
                event_type=event_type,
                actor=actor,
                date_from=date_from,
                date_to=date_to,
                tenant=tenant,
            )

        next_cursor = data[-1]['id'] if len(data) == limit else None

        return ok({
            'data': data,
            'next_cursor': next_cursor,
            'has_more': len(data) == limit,
            'total': total,
        })


class LogEventTypesHandler(HTTPEndpoint):
    @requires_permission(Permission.LOG_READ)
    async def get(self, request):
        async with get_conn() as conn:
            types = await AuditLog(conn).get_event_types()
        return ok({'data': types})


class LogActorsHandler(HTTPEndpoint):
    @requires_permission(Permission.LOG_READ)
    async def get(self, request):
        search = request.query_params.get('search')
        async with get_conn() as conn:
            actors = await AuditLog(conn).get_actors(search=search)
        return ok({'data': actors})
