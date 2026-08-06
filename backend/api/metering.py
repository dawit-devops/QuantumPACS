from starlette.endpoints import HTTPEndpoint

from api.permissions import Permission
from api.rbac import requires_permission
from api.response import api_error, not_found, ok
from config import config
from db.conn import get_conn
from db.metering import get_platform_usage, get_usage
from db.tenants import Tenants


def _clamp_days(request) -> int:
    """Days window from ?days=, bounded by the usage retention horizon."""
    retention = int(config.get('tenant_usage_retention_days', '365'))
    try:
        days = int(request.query_params.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    return max(1, min(days, retention))


class MeteringUsageHandler(HTTPEndpoint):
    @requires_permission(Permission.TENANT_READ)
    async def get(self, request):
        tenant_id = request.path_params['id']
        async with get_conn() as conn:
            tenant = await Tenants(conn).get(tenant_id)
            if not tenant:
                return not_found('Tenant not found')
            # Tenant-scoped admins may only read usage for their own tenant;
            # platform admins pass for any tenant id.
            if not getattr(request.user, 'admin', False) and (
                tenant.get('slug') != getattr(request.user, 'tenant', None)
            ):
                return api_error(
                    'FORBIDDEN',
                    'You do not have access to this tenant',
                    status=403,
                )
            slug = tenant['slug']
        usage_daily = await get_usage(slug, _clamp_days(request))
        totals = {
            'api_calls': sum(r['api_calls'] or 0 for r in usage_daily),
            'storage_bytes': (usage_daily[-1]['storage_bytes'] or 0) if usage_daily else 0,
            'active_users': max((r['active_users'] or 0) for r in usage_daily) if usage_daily else 0,
        }
        return ok({
            'tenant_id': tenant_id,
            'slug': slug,
            'usage_daily': usage_daily,
            'totals': totals,
        })


class PlatformUsageHandler(HTTPEndpoint):
    @requires_permission(Permission.METERING_READ)
    async def get(self, request):
        tenants = await get_platform_usage(_clamp_days(request))
        totals = {
            'api_calls': sum(t['api_calls'] or 0 for t in tenants),
            'storage_bytes': sum(t['storage_bytes'] or 0 for t in tenants),
            'active_users': sum(t['active_users'] or 0 for t in tenants),
        }
        return ok({'tenants': tenants, 'totals': totals})
