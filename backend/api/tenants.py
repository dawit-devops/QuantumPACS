from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.tenants import CreateTenantRequest, UpdateTenantRequest
from config import config
from db.conn import get_conn
from db.tenants import Tenants


class TenantsHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_READ)
    async def get(self, request):
        async with get_conn() as conn:
            tenants = await Tenants(conn).get_all()
        return ok({'data': tenants})

    @requires_permission(Permission.TENANT_ADMIN)
    async def post(self, request):
        body = await parse_body(CreateTenantRequest, request)
        async with get_conn() as conn:
            existing = await Tenants(conn).get_by_slug(body.slug)
            if existing:
                return ok({'error': 'Tenant slug already exists'})
            tenant_id = await Tenants(conn).create(
                name=body.name, slug=body.slug,
                domain=body.domain, db_name=body.db_name,
                db_host=body.db_host, db_port=body.db_port,
                db_user=body.db_user, db_password=body.db_password,
                storage_quota_bytes=body.storage_quota_bytes,
            )
        return created({'id': tenant_id})


class TenantHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_READ)
    async def get(self, request):
        tenant_id = request.path_params['id']
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
        if not tenant:
            return not_found('Tenant not found')
        return ok(tenant)

    @requires_permission(Permission.TENANT_ADMIN)
    async def put(self, request):
        tenant_id = request.path_params['id']
        body = await parse_body(UpdateTenantRequest, request)
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
            if not tenant:
                return not_found('Tenant not found')
            await Tenants(conn).patch(
                tenant_id,
                body.model_dump(exclude_none=True),
            )
        return ok({})

    @requires_permission(Permission.TENANT_ADMIN)
    async def delete(self, request):
        tenant_id = request.path_params['id']
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
            if not tenant:
                return not_found('Tenant not found')
            await Tenants(conn).delete(tenant_id)
        return ok({})


class TenantStatsHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_READ)
    async def get(self, request):
        tenant_id = request.path_params['id']
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
        if not tenant:
            return not_found('Tenant not found')
        slug = tenant['slug']
        pool_info = {
            'db_name': tenant.get('db_name', slug.replace('-', '_')),
            'db_host': tenant.get('db_host', config['db_host']),
            'db_port': tenant.get('db_port', config.get('db_port', '5432')),
            'db_user': tenant.get('db_user', config['db_user']),
            'db_password': config['db_password'],
        }
        stats = await Tenants(None).get_stats(slug, pool_info)
        return ok(stats)
