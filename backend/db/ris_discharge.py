"""Discharge planning checklist persistence (CC-06).

Template-based pre-discharge checklist (follow-up appointments, medication
reconciliation, patient education). Flat table: JSONB `items` holds each
item with label + done flag; overall checklist status derived per item.
sync_db self-heals; alembic migration 106 covers the container path.
"""


class DischargeChecklists:
    name = 'ris_discharge_checklists'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_discharge_checklists (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            patient_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'Discharge Checklist',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'completed')),
            items JSONB NOT NULL DEFAULT '[]'::jsonb,
            notes TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_discharge_patient"
            " ON ris_discharge_checklists(patient_id)")
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ris_discharge_tenant"
            " ON ris_discharge_checklists(tenant_id, status)")

    async def create(self, *, patient_id, title, items, notes, by,
                     tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO ris_discharge_checklists
               (patient_id, title, items, notes, created_by, tenant_id)
               VALUES ($1, $2, $3::jsonb, $4, $5, $6)
               RETURNING *""",
            str(patient_id), title, items, notes, str(by or ''), tenant_id,
        )
        return dict(row)

    async def get(self, checklist_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM ris_discharge_checklists WHERE id = $1 AND tenant_id = $2",
            str(checklist_id), tenant_id,
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
        sql = ("SELECT * FROM ris_discharge_checklists WHERE "
               + ' AND '.join(where)
               + f" ORDER BY updated_at DESC LIMIT ${len(params)+1}"
                 f" OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]

    async def update(self, *, checklist_id, status, items, notes,
                     tenant_id='default'):
        await self.conn.execute(
            """UPDATE ris_discharge_checklists
               SET status = $2, items = $3::jsonb, notes = $4, updated_at = now()
               WHERE id = $1 AND tenant_id = $5""",
            str(checklist_id), status, items, notes, tenant_id,
        )