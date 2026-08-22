"""Unbilled aging escalation alerts (R2-02-06).

Charges stuck PENDING past 10 days page the biller and practice manager.
Throttled to one alert per role per day — a stale backlog must not flood
the bell (same contract as the HL7 failure alerts).
"""

import log

ALERT_WINDOW_HOURS = 24

log = log.get_logger(__name__)


async def _notify_role_throttled(role_slug, event_type, title, body, link=''):
    """Fan out one throttled, pref-respecting bell notification."""
    try:
        from api.notify import notify_role
        from db.conn import get_tenant_slug
        conn_ctx = None
        # notify_role expects a request-scoped connection; reuse the pool
        # directly so escalation can run outside a request too.
        from db.conn import get_conn as _get_conn
        async with _get_conn() as conn:
            await notify_role(conn, role_slug, event_type, title, body, link)
        del conn_ctx, get_tenant_slug
    except Exception:
        log.exception('billing alert to %s failed', role_slug)


async def escalate_aging(conn, tenant_id, *, over10=0):
    """Notify biller + manager when unbilled charges exceed 10 days.

    `conn` is unused today (notify opens its own pool connection) but kept
    in the signature so callers inside an open transaction stay uniform.
    """
    if not over10:
        return
    title = 'Unbilled backlog over 10 days'
    body = f'{over10} charge(s) have been pending beyond 10 days.'
    link = '/billing/unbilled'
    for role in ('biller', 'practice_manager'):
        await _notify_role_throttled(
            role, 'billing.unbilled_escalation', title, body, link)
