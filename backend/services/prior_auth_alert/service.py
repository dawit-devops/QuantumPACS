"""Prior-auth expiry alert worker (R2-01-07).

Approved prior authorizations expiring within the alert window (default
7 days) trigger a notify_role alert so the payer team can request renewal
before the order becomes un-bookable. Also runs the expiry sweep
(APPROVED -> EXPIRED) so lapsed auths stop blocking the booking gate.
"""

from db.conn import get_conn
from db.ris_prior_auth import PriorAuth


class PriorAuthAlertEngine:
    def __init__(self, alert_days=7):
        self.alert_days = int(alert_days or 7)

    async def run_alert_check(self, tenant_id='default'):
        """Notify on expiring-soon approvals and expire overdue ones.

        Returns {'alerts': [...], 'expired': n} for tests/observability.
        """
        async with get_conn() as conn:
            expiring = await PriorAuth(conn).list_expiring_soon(
                self.alert_days, tenant_id)
            for row in expiring:
                await self._notify(conn, row)
            expired = await PriorAuth(conn).expire_overdue(tenant_id)
        # R2-01-15: expiring-soon gauge feeds the alert/manager surfaces.
        try:
            from api import telemetry
            telemetry.ris_prior_auth_expiring.set(float(len(expiring)))
        except Exception:
            pass
        return {'alerts': [dict(r) for r in expiring], 'expired': len(expired)}

    async def _notify(self, conn, row):
        from api.notify import notify_role
        order_id = row.get('order_id')
        expiry = row.get('expiry_date')
        await notify_role(
            conn, 'billing', 'prior_auth.expiring',
            f'Prior auth expiring: {row.get("payer_name", "")}',
            f'Order {order_id} prior auth expires {expiry} — request renewal.',
            f'/orders/{order_id}',
        )
