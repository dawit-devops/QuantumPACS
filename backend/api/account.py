import json

from starlette.endpoints import HTTPEndpoint
from api.response import ok, api_error, validation_error
from api.validate import parse_body
from api.schemas.account import UpdateProfileRequest
from api.schemas.users import UpdatePreferencesRequest
from db.audit_log import AuditLog
from db.conn import get_conn
from db.users import Users
from db.roles import Roles
from db.tenants import Tenants
from log import get_logger, request_id_var

log = get_logger(__name__)


class ProfileHandler(HTTPEndpoint):
    async def get(self, request):
        user_id = request.user.id
        async with get_conn() as conn:
            users_t = Users(conn)
            q = users_t.select(
                'id', 'username', 'email', 'created', 'role_id'
            ).where(users_t.table.id == user_id)
            row = await users_t.fetchone(q)
            if not row:
                return api_error('NOT_FOUND', 'User not found', status=404)

            role_slug = request.user.role_slug or ''
            role_name = ''
            if row.get('role_id'):
                role = await Roles(conn).get(row['role_id'])
                if role:
                    role_name = role.get('name', '')
                    role_slug = role.get('slug', '')

            tenant_name = ''
            if request.user.tenant:
                tenant = await Tenants(conn).get_by_slug(request.user.tenant)
                if tenant:
                    tenant_name = tenant.get('name', '')

            return ok({
                'id': row['id'],
                'username': row.get('username', ''),
                'email': row.get('email', ''),
                'role': role_slug,
                'role_display_name': role_name,
                'permissions': request.user.permissions,
                'tenant': request.user.tenant or '',
                'tenant_display_name': tenant_name,
                'created_at': str(row.get('created', '')) if row.get('created') else '',
                'last_login': str(row.get('last_login', '')) if row.get('last_login') else None,
            })

    async def put(self, request):
        body = await parse_body(UpdateProfileRequest, request)
        user_id = request.user.id

        async with get_conn() as conn:
            if body.email is not None:
                q = Users(conn).update().where(
                    Users(conn).table.id == user_id
                ).set(Users(conn).table.email, body.email)
                await conn.execute(str(q))

            return ok({'message': 'Profile updated'})


class PreferencesHandler(HTTPEndpoint):
    """Self-service per-user preference document (§3 dashboard layouts and
    future per-user settings). Same auth posture as /account/profile:
    authentication identifies the actor — no permission grant — and only
    the caller's own row is reachable. Top-level keys merge server-side so
    independent features never clobber each other's section."""

    MAX_DOCUMENT_BYTES = 65_536

    async def get(self, request):
        async with get_conn() as conn:
            prefs = await Users(conn).get_preferences(request.user.id)
        if prefs is None:
            return api_error('NOT_FOUND', 'User not found', status=404)
        return ok({'data': prefs})

    async def put(self, request):
        body = await parse_body(UpdatePreferencesRequest, request)
        doc = body.model_dump()
        if len(json.dumps(doc)) > self.MAX_DOCUMENT_BYTES:
            return validation_error('Preferences document exceeds 64 KB')
        async with get_conn() as conn:
            merged = await Users(conn).merge_preferences(request.user.id, doc)
            if merged is not None:
                await AuditLog(conn).log_event(
                    event_type='user.preferences_updated',
                    actor_id=request.user.id,
                    resource_type='user',
                    resource_id=str(request.user.id),
                    details={'keys': sorted(doc.keys())},
                    request_id=request_id_var.get(),
                )
        if merged is None:
            return api_error('NOT_FOUND', 'User not found', status=404)
        return ok({'data': merged})
