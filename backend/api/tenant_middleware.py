from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.response import not_found, apply_cors_headers
from config import config
from db.conn import get_conn, get_database, set_request_tenant, reset_request_tenant
from db.tenants import Tenants, TenantConnectionPool
from log import get_logger

log = get_logger(__name__)

# Statuses that block all data-plane access (clear 403) vs statuses that make
# the tenant invisible (404, as if it never existed).
_BLOCKED_STATUSES = frozenset({'suspended', 'quarantined'})
_INVISIBLE_STATUSES = frozenset({'decommissioned'})


def _main_db_acquire(tenant_info):
    """Return the main pool acquire callable when the tenant's data store IS
    the main database (the seeded `default` tenant), avoiding a second pool
    against the same database."""
    main_port = int(config.get('db_port', '5432'))
    if (
        tenant_info.get('db_name') == config['db_database']
        and tenant_info.get('db_host', config['db_host']) == config['db_host']
        and tenant_info.get('db_user', config['db_user']) == config['db_user']
        and int(tenant_info.get('db_port', main_port)) == main_port
        and tenant_info.get('db_password', config['db_password']) == config['db_password']
    ):
        return get_database().acquire
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        slug = None
        info = None
        user = getattr(request, 'user', None)
        authenticated = getattr(user, 'is_authenticated', False)

        # Priority (a): the JWT tenant claim always applies — the user's
        # tenant IS their data scope, header or not.
        if authenticated and getattr(user, 'tenant', None):
            slug = user.tenant

        # Priority (b): X-Tenant-ID header override — still gated through
        # can_access_tenant (admins pass for any slug). Anonymous requests
        # never get tenant scope from a header: public endpoints (login,
        # oauth, health) run un-scoped on the main pool, so a header can't
        # steer them into an attacker-chosen tenant's database.
        header_slug = request.headers.get('X-Tenant-ID')
        if header_slug and authenticated:
            if not user.can_access_tenant(header_slug):
                # TenantMiddleware sits outside CORSMiddleware; error
                # responses need explicit CORS headers or browsers block them.
                return apply_cors_headers(
                    request,
                    JSONResponse(
                        {'error': 'Forbidden',
                         'message': 'You do not have access to this tenant'},
                        status_code=403,
                    ),
                )
            slug = header_slug

        if slug:
            async with get_conn() as conn:
                info = await Tenants(conn).get_by_slug(slug)
            if not info:
                if header_slug:
                    # Header path keeps its historical contract: unknown
                    # tenant → 404.
                    return apply_cors_headers(request, not_found(f'Tenant not found: {slug}'))
                # Claim path: the tenant has no registry row (hard-deleted or
                # legacy account) — log and stay un-scoped (main-DB mode) so
                # the account keeps working.
                log.warning('Tenant claim %s has no registry row; request stays un-scoped', slug)
            else:
                status = info.get('status', 'active')
                if status in _INVISIBLE_STATUSES:
                    return apply_cors_headers(request, not_found(f'Tenant not found: {slug}'))
                if status in _BLOCKED_STATUSES:
                    return apply_cors_headers(
                        request,
                        JSONResponse(
                            {'error': 'Forbidden',
                             'message': f'Tenant is {status}'},
                            status_code=403,
                        ),
                    )
                pool = await TenantConnectionPool.get(slug, info)
                acquire = _main_db_acquire(info) or pool.acquire
                set_request_tenant(acquire)
                request.state.tenant = info
                request.state.tenant_slug = slug
                request.state.tenant_conn = acquire

        try:
            response = await call_next(request)
        finally:
            # Never leak a tenant scope into the next request on this task.
            reset_request_tenant()

        if slug and info:
            try:
                # Metering hook — db/metering.py is built by another stream;
                # degrade gracefully until it exists.
                from db.metering import record_request
                await record_request(slug)
            except Exception:
                pass

        return response


async def get_tenant_conn(request):
    slug = request.headers.get('X-Tenant-ID')
    if not slug:
        slug = getattr(request.state, 'tenant_slug', None)
    if not slug:
        return None

    async with get_conn() as conn:
        info = await Tenants(conn).get_by_slug(slug)
    if not info:
        return None

    main_acquire = _main_db_acquire(info)
    if main_acquire:
        return main_acquire()

    pool = TenantConnectionPool._pools.get(slug)
    if pool:
        return pool.acquire(timeout=10)

    pool = await TenantConnectionPool.get(slug, info)
    return pool.acquire(timeout=10)
