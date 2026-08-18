import csv
import io
import json

from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, forbidden
from api.tenant_middleware import effective_tenant
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
        download = request.query_params.get('download') == 'csv'
        # the web client serializes JS null to the literal string 'null'
        if cursor and cursor.lower() in ('null', 'none', ''):
            cursor = None
        limit = int(request.query_params.get('limit', 50))
        limit = max(10, min(200, limit))

        if event_type:
            event_type = event_type.split(',')

        user = request.user
        perms = getattr(user, 'permissions', [])

        # LO-02: the effective tenant scope (X-Tenant-ID override or JWT
        # claim) gates what audit rows a user can see — reading the home
        # tenant alone would let a cross-tenant operator leak the audited
        # activity of their current scope. The explicit ?tenant= filter keeps
        # its TENANT_READ gating for admins.
        tenant = effective_tenant(request)
        if tenant_filter:
            if Permission.TENANT_READ.value not in perms:
                return forbidden('Missing permission: TENANT_READ')
            tenant = tenant_filter

        async with get_conn() as conn:
            audit = AuditLog(conn)
            if download:
                # P2-2: export the FULL filtered result set server-side — the
                # old client-side CSV only ever had the current 50-row page.
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow([
                    'timestamp', 'actor', 'event_type', 'resource_type',
                    'resource_id', 'description', 'tenant', 'payload',
                ])
                row_cursor = cursor
                while True:
                    chunk = await audit.query(
                        event_type=event_type,
                        actor=actor,
                        date_from=date_from,
                        date_to=date_to,
                        tenant=tenant,
                        cursor=row_cursor,
                        limit=200,
                    )
                    for row in chunk:
                        writer.writerow([
                            row.get('created_at') or '',
                            row.get('actor') or '',
                            row.get('event_type') or '',
                            row.get('resource_type') or '',
                            row.get('resource_id') or '',
                            row.get('description') or '',
                            row.get('tenant') or '',
                            json.dumps(row.get('payload')),
                        ])
                    if len(chunk) < 200:
                        break
                    row_cursor = chunk[-1]['id']
                return Response(
                    content='\ufeff'.encode('utf-8') + buf.getvalue().encode('utf-8'),
                    media_type='text/csv',
                    headers={
                        'Content-Disposition': (
                            'attachment; filename="audit-logs-'
                            + str(date_from or 'all') + '.csv"'
                        ),
                    },
                )
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
