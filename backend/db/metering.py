"""Tenant usage metering — daily rollups of API calls, storage, and active users.

Backed by `tenant_usage_daily(slug, day, api_calls, storage_bytes, active_users,
PK(slug, day))` (migration 039) which lives in the platform (registry) database.

`record_request` is the interface the TenantMiddleware (Stream 1) calls on the
per-request hot path, so it must never raise — metering failures are logged and
swallowed, never allowed to break the request.
"""

from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)

_UPSERT_REQUEST_SQL = """
INSERT INTO tenant_usage_daily (slug, day, api_calls, storage_bytes, active_users)
VALUES ($1, CURRENT_DATE, 1, 0, 0)
ON CONFLICT (slug, day) DO UPDATE SET
    api_calls = tenant_usage_daily.api_calls + 1
"""

_UPSERT_STORAGE_SQL = """
INSERT INTO tenant_usage_daily (slug, day, api_calls, storage_bytes, active_users)
VALUES ($1, CURRENT_DATE, 0, $2, 0)
ON CONFLICT (slug, day) DO UPDATE SET
    storage_bytes = EXCLUDED.storage_bytes
"""


async def record_request(slug):
    """Increment today's api_calls counter for a tenant. Never raises."""
    try:
        async with get_conn() as conn:
            await conn.execute(_UPSERT_REQUEST_SQL, slug)
    except Exception:
        log.exception('metering: failed to record request for tenant %s', slug)


async def get_usage(slug, days=30):
    """Daily usage rows for the last `days` days (inclusive of today), oldest first."""
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT slug, day, api_calls, storage_bytes, active_users
            FROM tenant_usage_daily
            WHERE slug = $1 AND day >= CURRENT_DATE - $2::int
            ORDER BY day
            """,
            slug,
            max(days, 1),
        )
    return [dict(r) for r in rows]


async def get_platform_usage(days=30):
    """Per-tenant totals for the last `days` days, most active first.

    storage_bytes is the tenant's latest known storage total from the registry
    (tenants.storage_used_bytes) rather than a daily snapshot — it is the
    maintained source of truth for what the tenant currently holds.
    """
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT u.slug,
                   COALESCE(t.name, u.slug) AS name,
                   COALESCE(SUM(u.api_calls), 0) AS api_calls,
                   COALESCE(t.storage_used_bytes, 0) AS storage_bytes,
                   COALESCE(SUM(u.active_users), 0) AS active_users
            FROM tenant_usage_daily u
            LEFT JOIN tenants t ON t.slug = u.slug
            WHERE u.day >= CURRENT_DATE - $1::int
            GROUP BY u.slug, t.name, t.storage_used_bytes
            ORDER BY api_calls DESC
            """,
            max(days, 1),
        )
    return [dict(r) for r in rows]


async def record_storage(slug, bytes_):
    """Set today's storage_bytes row to the given total.

    Stream 1's persist_storage_used may call this after recalculating a
    tenant's actual usage, or it may be driven from the stats endpoint.
    """
    async with get_conn() as conn:
        await conn.execute(_UPSERT_STORAGE_SQL, slug, bytes_)


async def get_today_calls(slug):
    """API calls recorded for today, or 0 when the tenant has no row yet.

    Best-effort helper used by the health endpoint; missing rows or a missing
    usage table must not break the health probe.
    """
    try:
        async with get_conn() as conn:
            return await conn.fetchval(
                """
                SELECT api_calls FROM tenant_usage_daily
                WHERE slug = $1 AND day = CURRENT_DATE
                """,
                slug,
            ) or 0
    except Exception:
        return 0
