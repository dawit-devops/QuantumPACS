"""RIS Prior Authorization DB Layer (R2-01).

ris_prior_auth_requests holds the payer exchange for an order's prior
authorization. The order's prior_auth_status tag (ris_orders) is kept in
sync so the existing scheduling-gate check (engine.py C-7) sees APPROVED/
DENIED/EXPIRED without duplicating the decision logic. Status machine:
REQUIRED -> PENDING -> APPROVED | DENIED; APPROVED -> EXPIRED (date lapsed).
"""

from datetime import date, datetime

from db.table import Table


def _as_date(value):
    """Accept a date object or an ISO string; return None when empty."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class PriorAuth(Table):
    name = 'ris_prior_auth_requests'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_prior_auth_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            order_id UUID NOT NULL REFERENCES ris_orders(id),
            procedure_code TEXT NOT NULL DEFAULT '',
            cpt_code TEXT DEFAULT '',
            payer_id TEXT DEFAULT '',
            payer_name TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'REQUIRED'
                CHECK (status IN ('NOT_REQUIRED', 'REQUIRED', 'PENDING',
                                  'APPROVED', 'DENIED', 'EXPIRED')),
            auth_number TEXT DEFAULT '',
            approved_units INTEGER,
            approved_date DATE,
            expiry_date DATE,
            denial_reason TEXT DEFAULT '',
            requested_by TEXT DEFAULT '',
            decided_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)

    async def create_request(self, *, order_id, procedure_code='',
                             payer_id='', payer_name='', requested_by='',
                             tenant_id='default'):
        """Open a REQUIRED request and mark the order REQUIRED."""
        await self.conn.execute(
            "INSERT INTO ris_prior_auth_requests"
            " (tenant_id, order_id, procedure_code, payer_id, payer_name,"
            "  status, requested_by)"
            " VALUES ($1, $2, $3, $4, $5, 'REQUIRED', $6)",
            tenant_id, order_id, procedure_code, payer_id, payer_name,
            requested_by,
        )
        await self.conn.execute(
            "UPDATE ris_orders SET prior_auth_status = 'REQUIRED',"
            " updated_at = now() WHERE id = $1 AND tenant_id = $2",
            order_id, tenant_id,
        )

    async def submit_for_review(self, *, request_id, tenant_id='default'):
        """Move REQUIRED -> PENDING (payer review in flight)."""
        await self.conn.execute(
            "UPDATE ris_prior_auth_requests SET status = 'PENDING',"
            " updated_at = now() WHERE id = $1 AND tenant_id = $2"
            " AND status = 'REQUIRED'",
            request_id, tenant_id,
        )

    async def approve(self, *, request_id, auth_number='', approved_units=None,
                      approved_date=None, expiry_date=None, decided_by='',
                      tenant_id='default'):
        """Approve a request and sync the order status so the booking gate
        (engine.py C-7) accepts the order."""
        approved_date = _as_date(approved_date) or date.today()
        expiry_date = _as_date(expiry_date)
        result = await self.conn.fetchrow(
            "UPDATE ris_prior_auth_requests SET status = 'APPROVED',"
            " auth_number = $3, approved_units = $4, approved_date = $5,"
            " expiry_date = $6, decided_by = $7, updated_at = now()"
            " WHERE id = $1 AND tenant_id = $2 AND status = 'PENDING'"
            " RETURNING order_id",
            request_id, tenant_id, auth_number, approved_units,
            approved_date, expiry_date, decided_by,
        )
        if result:
            await self.conn.execute(
                "UPDATE ris_orders SET prior_auth_status = 'APPROVED',"
                " updated_at = now() WHERE id = $1 AND tenant_id = $2",
                result['order_id'], tenant_id,
            )
        return result

    async def deny(self, *, request_id, denial_reason='', decided_by='',
                   tenant_id='default'):
        """Deny a request and sync the order status (gate blocks DENIED)."""
        result = await self.conn.fetchrow(
            "UPDATE ris_prior_auth_requests SET status = 'DENIED',"
            " denial_reason = $3, decided_by = $4, updated_at = now()"
            " WHERE id = $1 AND tenant_id = $2 AND status = 'PENDING'"
            " RETURNING order_id",
            request_id, tenant_id, denial_reason, decided_by,
        )
        if result:
            await self.conn.execute(
                "UPDATE ris_orders SET prior_auth_status = 'DENIED',"
                " updated_at = now() WHERE id = $1 AND tenant_id = $2",
                result['order_id'], tenant_id,
            )
        return result

    async def expire_overdue(self, tenant_id='default'):
        """APPROVED requests whose expiry lapsed -> EXPIRED (order blocked)."""
        rows = await self.conn.fetch(
            "SELECT id, order_id FROM ris_prior_auth_requests"
            " WHERE tenant_id = $1 AND status = 'APPROVED'"
            "   AND expiry_date IS NOT NULL AND expiry_date < current_date",
            tenant_id,
        )
        for r in rows:
            await self.conn.execute(
                "UPDATE ris_prior_auth_requests SET status = 'EXPIRED',"
                " updated_at = now() WHERE id = $1",
                r['id'],
            )
            await self.conn.execute(
                "UPDATE ris_orders SET prior_auth_status = 'EXPIRED',"
                " updated_at = now() WHERE id = $1 AND tenant_id = $2",
                r['order_id'], tenant_id,
            )
        return rows

    async def list_expiring_soon(self, days=7, tenant_id='default'):
        """APPROVED requests expiring within `days` (R2-01-07 alerts)."""
        return await self.conn.fetch(
            "SELECT id, order_id, auth_number, expiry_date, payer_name"
            " FROM ris_prior_auth_requests"
            " WHERE tenant_id = $1 AND status = 'APPROVED'"
            "   AND expiry_date IS NOT NULL"
            "   AND expiry_date <= current_date + $2::int"
            "   AND expiry_date >= current_date"
            " ORDER BY expiry_date",
            tenant_id, days,
        )

    async def get(self, request_id, tenant_id='default'):
        return await self.conn.fetchrow(
            "SELECT * FROM ris_prior_auth_requests"
            " WHERE id = $1 AND tenant_id = $2",
            request_id, tenant_id,
        )

    async def list(self, tenant_id='default', status=None, limit=100, offset=0):
        conditions = ['tenant_id = $1']
        params = [tenant_id]
        idx = 2
        if status:
            conditions.append(f'status = ${idx}')
            params.append(status)
            idx += 1
        where = ' AND '.join(conditions)
        rows = await self.conn.fetch(
            f"SELECT * FROM ris_prior_auth_requests WHERE {where}"
            f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params, limit, offset,
        )
        total = await self.conn.fetchval(
            f"SELECT count(*) FROM ris_prior_auth_requests WHERE {where}",
            *params,
        )
        return [dict(r) for r in rows], total or 0
