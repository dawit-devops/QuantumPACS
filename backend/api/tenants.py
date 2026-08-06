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
from db.tenants import Tenants, TenantConnectionPool
from log import request_id_var

# Audit events emitted on tenant status transitions via PUT.
_STATUS_EVENTS = {
    'active': 'tenant.activated',
    'suspended': 'tenant.suspended',
    'quarantined': 'tenant.quarantined',
    'decommissioned': 'tenant.decommissioned',
}
# Statuses that must drop the tenant's live connection pools immediately.
_GATING_STATUSES = frozenset({'suspended', 'quarantined', 'decommissioned'})
# Fields that re-point the tenant's data store or gate access — changing these
# requires the platform super admin, never a tenant-scoped admin.
_ADMIN_ONLY_FIELDS = frozenset(
    {'status', 'db_name', 'db_host', 'db_port', 'db_user', 'db_password'}
)


def _is_platform_admin(user) -> bool:
    """Platform admins (super_admin / legacy admin flag) manage all tenants;
    every other TENANT_* holder is confined to their own tenant."""
    return bool(getattr(user, 'admin', False))


def _owns_tenant(user, slug) -> bool:
    if _is_platform_admin(user):
        return True
    return bool(slug) and getattr(user, 'tenant', None) == slug


def _tenant_scoped_403(message='You do not have access to this tenant'):
    return api_error('FORBIDDEN', message, status=403)


class TenantsHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_READ)
    async def get(self, request):
        include_decommissioned = request.query_params.get('include_decommissioned') == 'true'
        if include_decommissioned and not _is_platform_admin(request.user):
            # Decommissioned tenants are invisible to everyone but the
            # platform super admin.
            return api_error(
                'FORBIDDEN',
                'Only super admins may list decommissioned tenants',
                status=403,
            )
        async with get_conn() as conn:
            tenants = await Tenants(conn).get_all(
                include_decommissioned=include_decommissioned,
            )
        if not _is_platform_admin(request.user):
            # Tenant-scoped admins only ever see their own tenant.
            own = getattr(request.user, 'tenant', None)
            tenants = [t for t in tenants if t.get('slug') == own]
        return ok({'data': tenants})

    @requires_permission(Permission.TENANT_ADMIN)
    async def post(self, request):
        if not _is_platform_admin(request.user):
            # Provisioning creates a real database and an initial admin —
            # a platform-level action, never a tenant-scoped one.
            return _tenant_scoped_403('Only platform admins may provision tenants')
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
            plan=body.plan,
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
        if not _owns_tenant(request.user, tenant.get('slug')):
            return _tenant_scoped_403()
        return ok(tenant)

    @requires_permission(Permission.TENANT_ADMIN)
    async def put(self, request):
        tenant_id = request.path_params['id']
        body = await parse_body(UpdateTenantRequest, request)
        status = None
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
            if not tenant:
                return not_found('Tenant not found')
            data = body.model_dump(exclude_none=True)
            if not _owns_tenant(request.user, tenant.get('slug')):
                return _tenant_scoped_403()
            if not _is_platform_admin(request.user) and (
                set(data) & _ADMIN_ONLY_FIELDS
            ):
                # Status transitions and DB endpoint re-pointing are
                # platform-level; a tenant-scoped admin may only touch
                # name/domain/plan/quota on their own tenant.
                return _tenant_scoped_403(
                    'Status and database settings require platform admin'
                )
            await Tenants(conn).patch(
                tenant_id,
                data,
            )
            status = data.get('status')
            if status and status != tenant.get('status'):
                await AuditLog(conn).log_event(
                    event_type=_STATUS_EVENTS.get(status, 'tenant.status_changed'),
                    actor_id=request.user.id,
                    resource_type='tenant',
                    resource_id=tenant_id,
                    details={'from': tenant.get('status'), 'to': status},
                    tenant=tenant.get('slug'),
                    request_id=request_id_var.get(),
                )
        if status in _GATING_STATUSES:
            await TenantConnectionPool.close(tenant['slug'])
        return ok({})

    @requires_permission(Permission.TENANT_ADMIN)
    async def delete(self, request):
        if not _is_platform_admin(request.user):
            # Decommissioning a tenant (even your own) is a platform action.
            return _tenant_scoped_403('Only platform admins may decommission tenants')
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
            if not _owns_tenant(request.user, tenant.get('slug')):
                return _tenant_scoped_403()
            slug = tenant['slug']
            # Internal accessor only — db_password must never leave it into a
            # handler response; get_stats() below returns an explicit dict.
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
