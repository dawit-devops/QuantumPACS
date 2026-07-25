from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.roles import CreateRoleRequest, UpdateRoleRequest
from db.conn import get_conn
from db.roles import Roles


class RolesHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        async with get_conn() as conn:
            roles = await Roles(conn).get_all()
        return ok({'data': roles})

    @requires_permission(Permission.ROLE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateRoleRequest, request)
        async with get_conn() as conn:
            role_id = await Roles(conn).create(
                name=body.name,
                slug=body.slug,
                permissions=body.permissions,
            )
        return created({'id': role_id})


class RoleHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        role_id = request.path_params['id']
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
        if not role:
            return not_found('Role not found')
        return ok(role)

    @requires_permission(Permission.ROLE_WRITE)
    async def put(self, request):
        role_id = request.path_params['id']
        body = await parse_body(UpdateRoleRequest, request)
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
            if not role:
                return not_found('Role not found')
            await Roles(conn).patch(
                role_id,
                body.model_dump(exclude_none=True),
            )
        return ok({})

    @requires_permission(Permission.ROLE_DELETE)
    async def delete(self, request):
        role_id = request.path_params['id']
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
            if not role:
                return not_found('Role not found')
            if role.get('built_in'):
                return ok({'error': 'Cannot delete built-in role'})
            await Roles(conn).delete(role_id)
        return ok({})
