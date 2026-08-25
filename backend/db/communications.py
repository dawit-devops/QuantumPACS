"""Communications persistence (CS7/CC-04).

Inbound/outbound correspondence trail per patient — distinct from the
care-contact `encounters` table. Search is patient-scoped; writes are
append-only (the log is an audit surface, not a workflow state).
"""



class Communications:
    name = 'communications'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            direction TEXT NOT NULL
                CHECK (direction IN ('inbound', 'outbound')),
            channel TEXT NOT NULL DEFAULT 'phone',
            category TEXT DEFAULT '',
            summary TEXT NOT NULL,
            related_order_id TEXT DEFAULT '',
            logged_by TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_communications_patient_time"
            " ON communications(tenant_id, patient_id, created_at DESC)")

    async def create(self, *, patient_id, direction, channel, summary,
                     category='', related_order_id='', by='',
                     tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO communications
               (patient_id, direction, channel, category, summary,
                related_order_id, logged_by, tenant_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               RETURNING *""",
            str(patient_id), direction, channel, category, summary,
            str(related_order_id or ''), str(by or ''), tenant_id,
        )
        return dict(row)

    async def list(self, tenant_id='default', patient_id=None, limit=200):
        if not patient_id:
            return []
        rows = await self.conn.fetch(
            """SELECT * FROM communications
               WHERE tenant_id = $1 AND patient_id = $2
               ORDER BY created_at DESC LIMIT $3""",
            tenant_id, str(patient_id), max(int(limit), 1),
        )
        return [dict(r) for r in rows]
