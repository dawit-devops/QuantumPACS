"""Referral tracking persistence (CC-05).

Tracks referrals from an ordering provider to a specialist through the
pending -> accepted -> completed lifecycle, optionally linked to an order
and a follow-up report. Flat table, tenant isolated, sync_db self-heals;
alembic migration 105 covers the container path.
"""


class Referrals:
    name = 'ris_referrals'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_referrals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            patient_id TEXT NOT NULL,
            from_provider TEXT DEFAULT '',
            to_specialist TEXT NOT NULL,
            specialty TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'completed', 'cancelled')),
            order_id TEXT DEFAULT '',
            report_id TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_referrals_patient"
            " ON ris_referrals(patient_id)")
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_referrals_tenant"
            " ON ris_referrals(tenant_id, status)")

    async def create(self, *, patient_id, from_provider, to_specialist,
                     specialty, order_id, report_id, notes, by,
                     tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO ris_referrals
               (patient_id, from_provider, to_specialist, specialty,
                order_id, report_id, notes, created_by, tenant_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            str(patient_id), from_provider, to_specialist, specialty,
            order_id or '', report_id or '', notes, str(by or ''), tenant_id,
        )
        return dict(row)

    async def get(self, referral_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM ris_referrals WHERE id = $1 AND tenant_id = $2",
            str(referral_id), tenant_id,
        )
        return dict(row) if row else None

    async def list(self, tenant_id='default', status=None, patient_id=None,
                   limit=200, offset=0):
        where = ['tenant_id = $1']
        params = [tenant_id]
        if status:
            params.append(status)
            where.append(f'status = ${len(params)}')
        if patient_id:
            params.append(str(patient_id))
            where.append(f'patient_id = ${len(params)}')
        sql = ("SELECT * FROM ris_referrals WHERE "
               + ' AND '.join(where)
               + f" ORDER BY updated_at DESC LIMIT ${len(params)+1}"
                 f" OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]

    async def update(self, *, referral_id, status, notes, tenant_id='default'):
        await self.conn.execute(
            """UPDATE ris_referrals SET status = $2, notes = $3, updated_at = now()
               WHERE id = $1 AND tenant_id = $4""",
            str(referral_id), status, notes, tenant_id,
        )