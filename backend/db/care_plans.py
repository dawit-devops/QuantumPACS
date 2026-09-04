"""Care plans persistence (CS5/CC-02).

Flat table: JSONB `tasks` keeps each plan single-row; `status` drives the
coordinator board (active / on_hold / completed). `sync_db` creates the
table so the RIS page works even before the alembic migration runs in dev.
"""


class CarePlans:
    name = 'care_plans'

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS care_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'completed', 'on_hold')),
            tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
            responsible_provider TEXT DEFAULT '',
            follow_up_at TIMESTAMPTZ,
            notes TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_care_plans_patient"
            " ON care_plans(patient_id)")
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_care_plans_status"
            " ON care_plans(tenant_id, status)")

    async def create(self, *, patient_id, title, tasks, responsible_provider,
                     follow_up_at, notes, by, tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            """INSERT INTO care_plans
               (patient_id, title, tasks, responsible_provider,
                follow_up_at, notes, created_by, tenant_id)
               VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8)
               RETURNING *""",
            str(patient_id), title, tasks, responsible_provider,
            follow_up_at, notes, str(by or ''), tenant_id,
        )
        return dict(row)

    async def update(self, *, plan_id, title, status, tasks,
                     responsible_provider, follow_up_at, notes,
                     tenant_id='default'):
        await self.conn.execute(
            """UPDATE care_plans SET title = $2, status = $3, tasks = $4::jsonb,
               responsible_provider = $5, follow_up_at = $6, notes = $7,
               updated_at = now()
               WHERE id = $1 AND tenant_id = $8""",
            str(plan_id), title, status, tasks, responsible_provider,
            follow_up_at, notes, tenant_id,
        )

    async def get(self, plan_id, tenant_id='default'):
        row = await self.conn.fetchrow(
            "SELECT * FROM care_plans WHERE id = $1 AND tenant_id = $2",
            str(plan_id), tenant_id,
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
        sql = ("SELECT * FROM care_plans WHERE "
               + ' AND '.join(where)
               + f" ORDER BY updated_at DESC LIMIT ${len(params)+1}"
                 f" OFFSET ${len(params)+2}")
        rows = await self.conn.fetch(sql, *params, max(int(limit), 1),
                                     max(int(offset), 0))
        return [dict(r) for r in rows]
