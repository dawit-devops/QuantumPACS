from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.auth import can_access_tenant, can_mutate_tenant, _is_read_method
from api.response import not_found, apply_cors_headers
from db.audit_log import AuditLog
from db.conn import (
    get_conn, get_database, set_request_tenant, reset_request_tenant,
    set_tenant_slug, reset_tenant_slug,
)
from db.tenants import Tenants, TenantConnectionPool, uses_main_database
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
    if uses_main_database(tenant_info):
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
        # can_access_tenant (admins pass for any slug; CROSS_TENANT_READ
        # holders only for tenants with an explicit user_tenant_grants row,
        # R2-03). Anonymous requests never get tenant scope from a header:
        # public endpoints (login, oauth, health) run un-scoped on the main
        # pool, so a header can't steer them into an attacker-chosen tenant's
        # database.
        header_slug = request.headers.get('X-Tenant-ID')
        cross_tenant = False
        if header_slug and authenticated:
            if not await can_access_tenant(user, header_slug):
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
            # Grant-based overrides are the audit-worthy events: the user is
            # operating outside their home tenant via a user_tenant_grants
            # row, not via an admin flag. Logged below, before any data-plane
            # work, on the main pool.
            cross_tenant = not user.admin and user.tenant != header_slug
            if cross_tenant:
                # Read-scoped grants (teleradiology) see the tenant but must
                # not mutate it: deny non-GET/HEAD and every WebSocket
                # channel unless the grant row explicitly says 'write'.
                method = request.scope.get('method', '')
                if request.scope.get('type') == 'websocket' or not _is_read_method(method):
                    if not await can_mutate_tenant(user, header_slug):
                        return apply_cors_headers(
                            request,
                            JSONResponse(
                                {'error': 'Forbidden',
                                 'message': 'Read-only access to this tenant'},
                                status_code=403,
                            ),
                        )

        if slug:
            async with get_conn() as conn:
                info = await Tenants(conn).get_by_slug(slug)
                if cross_tenant:
                    await AuditLog(conn).log_event(
                        'tenant.cross_tenant_access',
                        str(user.id),
                        'tenant',
                        slug,
                        details={'home': getattr(user, 'tenant', None)},
                        tenant=slug,
                    )
            if not info:
                if header_slug:
                    # Header path keeps its historical contract: unknown
                    # tenant → 404.
                    return apply_cors_headers(request, not_found(f'Tenant not found: {slug}'))
                # Claim path (R5-04): a JWT tenant with no registry row
                # (hard-deleted or decommissioned tenant) must NOT fall back
                # to the main DB — that would silently re-scope the user into
                # the default tenant's data plane. Fail closed with 403.
                log.warning('Tenant claim %s has no registry row; rejecting request', slug)
                return apply_cors_headers(
                    request,
                    JSONResponse(
                        {'error': 'Forbidden',
                         'message': f'Tenant not available: {slug}'},
                        status_code=403,
                    ),
                )
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
                set_tenant_slug(slug)
                request.state.tenant = info
                request.state.tenant_slug = slug
                request.state.tenant_conn = acquire

                if cross_tenant and not uses_main_database(info):
                    # N5: the gate event was recorded on the main DB above,
                    # but tenant-scoped log readers query the tenant's own
                    # logs table (LO-02) — for separate-DB tenants the main
                    # row is invisible there. Mirror the row on the resolved
                    # tenant pool so both views carry the event; failure must
                    # never gate the request itself.
                    try:
                        async with acquire() as tconn:
                            await AuditLog(tconn).log_event(
                                'tenant.cross_tenant_access',
                                str(user.id),
                                'tenant',
                                slug,
                                details={'home': getattr(user, 'tenant', None)},
                                tenant=slug,
                            )
                    except Exception:
                        log.warning(
                            'Tenant-pool audit write failed for %s', slug, exc_info=True,
                        )

        try:
            response = await call_next(request)
        finally:
            # Never leak a tenant scope into the next request on this task.
            reset_request_tenant()
            reset_tenant_slug()
            if slug and info:
                # ME-02: drop the pool lease taken by TenantConnectionPool.get
                # above — without this the LRU eviction skips the pool forever
                # and per-tenant pools leak past _max_pools.
                if not uses_main_database(info):
                    TenantConnectionPool.release(slug)

        if slug and info:
            try:
                # Metering hook — db/metering.py is built by another stream;
                # degrade gracefully until it exists.
                from db.metering import record_request
                await record_request(slug)
            except Exception:
                log.debug('Metering record failed for tenant %s', slug, exc_info=True)

        return response


def effective_tenant(request):
    """The tenant scope actually in effect for this request — the
    middleware-resolved slug when one is in effect (header override or JWT
    claim), otherwise the user's home tenant. Audit rows must record the
    effective scope (R5-05): under X-Tenant-ID, the JWT claim is the home
    tenant, not where the mutation actually landed."""
    slug = getattr(getattr(request, 'state', None), 'tenant_slug', None)
    if isinstance(slug, str) and slug:
        return slug
    return getattr(request.user, 'tenant', None)
