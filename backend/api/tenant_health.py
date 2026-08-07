"""Tenant health probe — reachability of each tenant's database.

Runs a trivial `SELECT 1` against every non-decommissioned tenant's pool with a
short timeout; one unhealthy tenant must never fail the whole response, so each
tenant gets its own entry with an `error` field when the probe fails.
"""

import asyncio
import time

from starlette.endpoints import HTTPEndpoint

from api.permissions import Permission
from api.rbac import requires_permission
from api.response import ok
from config import config
from db.conn import get_conn
from db.metering import get_today_calls
from db.tenants import TenantConnectionPool, Tenants

_PROBE_TIMEOUT = 3.0


def _storage_pct(tenant):
    quota = tenant.get('storage_quota_bytes') or 0
    used = tenant.get('storage_used_bytes') or 0
    return round((used / quota) * 100, 1) if quota else 0


def _connection_info(tenant):
    slug = tenant['slug']
    return {
        'db_name': tenant.get('db_name') or slug.replace('-', '_'),
        'db_host': tenant.get('db_host') or config['db_host'],
        'db_port': tenant.get('db_port') or config.get('db_port', '5432'),
        'db_user': tenant.get('db_user') or config['db_user'],
        'db_password': tenant.get('db_password') or config['db_password'],
    }


async def _probe_tenant(tenant: dict) -> dict:
    """Probe one tenant DB; always returns a dict, never raises."""
    result = {
        'slug': tenant['slug'],
        'name': tenant.get('name'),
        'status': tenant.get('status', 'active'),
        'db_reachable': False,
        'latency_ms': None,
        'last_activity': None,
        'storage_pct': _storage_pct(tenant),
        'api_calls_today': await get_today_calls(tenant['slug']),
        'error': None,
    }
    pool = None
    conn = None
    try:
        pool = await TenantConnectionPool.get(tenant['slug'], _connection_info(tenant))
        conn = await asyncio.wait_for(pool.acquire(), timeout=_PROBE_TIMEOUT)
        started = time.monotonic()
        await asyncio.wait_for(conn.fetchval('SELECT 1'), timeout=_PROBE_TIMEOUT)
        result['latency_ms'] = round((time.monotonic() - started) * 1000, 1)
        result['db_reachable'] = True
        try:
            last = await asyncio.wait_for(
                conn.fetchval('SELECT MAX(created) FROM files'),
                timeout=_PROBE_TIMEOUT,
            )
            result['last_activity'] = str(last) if last else None
        except Exception:
            pass  # last_activity stays None — reachability is the health signal
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if conn is not None and pool is not None:
            try:
                await pool.release(conn)
            except Exception:
                pass
    return result


class TenantHealthHandler(HTTPEndpoint):
    # Platform-level probe of every tenant's database — tenant-scoped admins
    # must not see cross-tenant operational data.
    @requires_permission(Permission.METERING_READ)
    async def get(self, request):
        async with get_conn() as conn:
            tenants = await Tenants(conn).get_all()
            # get_all() strips db_password; fetch the full row for connection info
            registry = {
                t['slug']: (await Tenants(conn).get_by_slug(t['slug'])) or t
                for t in tenants
            }
        results = await asyncio.gather(
            *[_probe_tenant(registry[t['slug']]) for t in tenants]
        )
        return ok({'tenants': results})
