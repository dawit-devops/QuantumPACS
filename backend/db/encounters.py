"""Encounters persistence (CS6/CC-03).

Patient-scoped contact log: visit / call / message / fax rows with an
occurred_at timeline ordering. Optionally linked to a RIS order or a
report so the chart tab can deep-link context.
"""



class Encounters:
    name = 'encounters'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS encounters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            encounter_type TEXT NOT NULL
                CHECK (encounter_type IN ('visit', 'call', 'message', 'fax')),
            occurred_at TIMESTAMPTZ DEFAULT now(),
            summary TEXT NOT NULL,
            linked_order_id TEXT DEFAULT '',
            linked_report_id TEXT DEFAULT '',
            recorded_by TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_encounters_patient_time"
            " ON encounters(tenant_id, patient_id, occurred_at DESC)")

    async def create(self, *, patient_id, encounter_type, summary,
                     occurred_at=None, linked_order_id='',
                     linked_report_id='', by='', tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO encounters
               (patient_id, encounter_type, occurred_at, summary,
                linked_order_id, linked_report_id, recorded_by, tenant_id)
               VALUES ($1, $2, COALESCE($3::timestamptz, now()),
                       $4, $5, $6, $7, $8)
               RETURNING *""",
            str(patient_id), encounter_type, occurred_at, summary,
            str(linked_order_id or ''), str(linked_report_id or ''),
            str(by or ''), tenant_id,
        )
        return dict(row)

    async def list(self, tenant_id='default', patient_id=None, limit=200):
        if not patient_id:
            return []
        rows = await self.conn.fetch(
            """SELECT * FROM encounters
               WHERE tenant_id = $1 AND patient_id = $2
               ORDER BY occurred_at DESC LIMIT $3""",
            tenant_id, str(patient_id), max(int(limit), 1),
        )
        return [dict(r) for r in rows]
