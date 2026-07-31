from starlette.endpoints import HTTPEndpoint
from api.response import ok, api_error
from api.validate import parse_body
from api.schemas.account import UpdateProfileRequest
from db.conn import get_conn
from db.users import Users
from db.roles import Roles
from db.tenants import Tenants
from log import get_logger

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
