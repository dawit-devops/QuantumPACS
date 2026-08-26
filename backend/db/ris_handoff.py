"""Handoff notes persistence (CC-08).

Per-patient handoff notes visible to the next coordinator. Flat table:
priority flags (low/normal/high/urgent), read/unread tracking, tenant
isolation. sync_db creates the table; the alembic migration (hand-written)
adds it for the container path.
"""


class HandoffNotes:
    name = 'ris_handoff_notes'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_handoff_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            is_read BOOLEAN NOT NULL DEFAULT false,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_handoff_notes_patient"
            " ON ris_handoff_notes(patient_id)")
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_handoff_notes_tenant"
            " ON ris_handoff_notes(tenant_id, created_at DESC)")

    async def create(self, *, patient_id, note, priority, by, tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO ris_handoff_notes
               (patient_id, note, priority, created_by, tenant_id)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING *""",
            str(patient_id), note, priority, str(by or ''), tenant_id,
        )
        return dict(row)

    async def get(self, note_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM ris_handoff_notes WHERE id = $1 AND tenant_id = $2",
            str(note_id), tenant_id,
        )
        return dict(row) if row else None

    async def list(self, tenant_id='default', patient_id=None, unread_only=False,
                   limit=100, offset=0):
        where = ['tenant_id = $1']
        params = [tenant_id]
        if patient_id:
            params.append(str(patient_id))
            where.append(f'patient_id = ${len(params)}')
        if unread_only:
            params.append(False)
            where.append(f'is_read = ${len(params)}')
        sql = ("SELECT * FROM ris_handoff_notes WHERE "
               + ' AND '.join(where)
               + f" ORDER BY priority DESC, created_at DESC"
                 f" LIMIT ${len(params)+1} OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]

    async def mark_read(self, note_id, tenant_id='default'):
        await self.conn.execute(
            "UPDATE ris_handoff_notes SET is_read = true WHERE id = $1 AND tenant_id = $2",
            str(note_id), tenant_id,
        )