from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.response import not_found
from db.conn import get_conn
from db.tenants import Tenants, TenantConnectionPool


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        slug = request.headers.get('X-Tenant-ID')
        if slug:
            user = request.user
            if user.is_authenticated and not user.can_access_tenant(slug):
                return JSONResponse(
                    {'error': 'Forbidden',
                     'message': 'You do not have access to this tenant'},
                    status_code=403,
                )
            async with get_conn() as conn:
                info = await Tenants(conn).get_by_slug(slug)
            if not info:
                return not_found(f'Tenant not found: {slug}')
            pool = await TenantConnectionPool.get(slug, info)
            request.state.tenant = info
            request.state.tenant_slug = slug
            request.state.tenant_conn = pool.acquire

        response = await call_next(request)
        return response


async def get_tenant_conn(request):
    slug = request.headers.get('X-Tenant-ID')
    if not slug:
        slug = getattr(request.state, 'tenant_slug', None)
    if not slug:
        return None

    pool = TenantConnectionPool._pools.get(slug)
    if pool:
        return pool.acquire(timeout=10)

    async with get_conn() as conn:
        info = await Tenants(conn).get_by_slug(slug)
    if not info:
        return None

    pool = await TenantConnectionPool.get(slug, info)
    return pool.acquire(timeout=10)
