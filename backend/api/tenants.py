from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException

from api.rbac import requires_permission, has_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error, forbidden
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
# Fields that re-point the tenant's data store: a live pool created with the
# old connection config must be closed so the next request re-connects (HI-3).
_DB_FIELDS = frozenset({'db_name', 'db_host', 'db_port', 'db_user', 'db_password'})


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


def _pool_info_for(tenant: dict) -> dict:
    """Connection info for a tenant registry row — the internal accessor only;
    db_password must never leave it into a handler response (get_stats returns
    an explicit dict). Shared by the list enrichment and TenantStatsHandler."""
    slug = tenant['slug']
    return {
        'db_name': tenant.get('db_name') or slug.replace('-', '_'),
        'db_host': tenant.get('db_host') or config['db_host'],
        'db_port': tenant.get('db_port') or config.get('db_port', '5432'),
        'db_user': tenant.get('db_user') or config['db_user'],
        'db_password': tenant.get('db_password') or config['db_password'],
    }


class TenantsHandler(HTTPEndpoint):
    async def get(self, request):
        user = request.user
        if not user.is_authenticated:
            raise HTTPException(status_code=401, detail='Not authenticated')
        # Replacement for the old TENANT_READ-only decorator: CROSS_TENANT_READ
        # holders (radiologist/teleradiologist) also need the list — it is the
        # only way the sidebar tenant switcher can surface their RT-301 grants.
        tenant_reader = has_permission(user, Permission.TENANT_READ)
        cross_reader = has_permission(user, Permission.CROSS_TENANT_READ)
        if not (tenant_reader or cross_reader):
            return forbidden(f'Missing permission: {Permission.TENANT_READ.value}')
        include_decommissioned = request.query_params.get('include_decommissioned') == 'true'
        if include_decommissioned and not _is_platform_admin(user):
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
        if not _is_platform_admin(user):
            # TENANT_READ holders see only their own tenant (historical
            # scoping); a pure CROSS_TENANT_READ reader has no TENANT_READ
            # scoping rules to inherit, so show exactly the tenants their
            # grant rows unlock, plus their home tenant.
            own = getattr(user, 'tenant', None)
            if tenant_reader:
                tenants = [t for t in tenants if t.get('slug') == own]
            else:
                from db.user_tenant_grants import UserTenantGrants
                async with get_conn() as conn:
                    grants = await UserTenantGrants(conn).list_for_user(user.id)
                granted = {g['tenant_slug'] for g in grants}
                tenants = [
                    t for t in tenants
                    if t.get('slug') == own or t.get('slug') in granted
                ]
        # P2-1 (tenant_admin review): the tenant card must show real counts,
        # not permanent "?" placeholders. Enrich the visible (scoped) list
        # with per-tenant stats — the scoped case is the user's own tenant,
        # so this is one cheap aggregate; platform admins see every tenant
        # enriched the same way.
        enriched = []
        for t in tenants:
            try:
                stats = await Tenants(None).get_stats(
                    t['slug'], _pool_info_for(t),
                    storage_quota_bytes=t.get('storage_quota_bytes', 0),
                )
            except Exception:
                # A tenant whose DB pool cannot be opened (e.g. decommissioned
                # or transiently down) must not 500 the whole list — the card
                # degrades to the values the registry row already carries.
                stats = {}
            row = dict(t)
            row.update({k: stats.get(k) for k in (
                'user_count', 'study_count', 'file_count', 'last_activity',
            )})
            enriched.append(row)
        return ok({'data': enriched})

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
        if status in _GATING_STATUSES or (set(data) & _DB_FIELDS):
            # Gating statuses and DB-endpoint changes both invalidate the
            # tenant's live pool: it must be recreated from the registry row
            # on the next request (HI-3 — a stale pool would keep pointing
            # at the old host/credentials).
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
        pool_info = _pool_info_for(info if info else tenant)
        stats = await Tenants(None).get_stats(slug, pool_info, storage_quota_bytes=tenant.get('storage_quota_bytes', 0))
        return ok(stats)
