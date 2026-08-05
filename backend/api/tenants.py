from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error
from api.validate import parse_body
from api.schemas.tenants import CreateTenantRequest, UpdateTenantRequest
from config import config
from db.audit_log import AuditLog
from db.conn import get_conn
from db.tenant_provisioner import TenantProvisioner
from db.tenants import Tenants
from log import request_id_var


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
                return api_error('CONFLICT', 'Tenant slug already exists', status=409)

        result = await TenantProvisioner.provision(
            slug=body.slug, name=body.name,
            domain=body.domain, db_name=body.db_name,
            db_host=body.db_host, db_port=body.db_port,
            db_user=body.db_user, db_password=body.db_password,
            storage_quota_bytes=body.storage_quota_bytes,
            admin_email=body.admin_email,
        )

        async with get_conn() as conn:
            await AuditLog(conn).log_event(
                event_type='tenant.provisioned',
                actor_id=request.user.id,
                resource_type='tenant',
                resource_id=result['tenant_id'],
                details={'name': body.name, 'slug': body.slug},
                tenant=body.slug,
                request_id=request_id_var.get(),
            )
        return created({
            'id': result['tenant_id'],
            'admin_password': result.get('admin_password'),
        })


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
            await AuditLog(conn).log_event(
                event_type='tenant.deleted',
                actor_id=request.user.id,
                resource_type='tenant',
                resource_id=tenant_id,
                details={'name': tenant.get('name'), 'slug': tenant.get('slug')},
                tenant=tenant.get('slug'),
                request_id=request_id_var.get(),
            )
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
            info = await Tenants(conn).get_connection_info(tenant_id)
        pool_info = {
            'db_name': info.get('db_name', slug.replace('-', '_')) if info else slug.replace('-', '_'),
            'db_host': info.get('db_host', config['db_host']) if info else config['db_host'],
            'db_port': info.get('db_port', config.get('db_port', '5432')) if info else config.get('db_port'),
            'db_user': info.get('db_user', config['db_user']) if info else config['db_user'],
            'db_password': info.get('db_password', config['db_password']) if info else config['db_password'],
        }
        stats = await Tenants(None).get_stats(slug, pool_info, storage_quota_bytes=tenant.get('storage_quota_bytes', 0))
        return ok(stats)
