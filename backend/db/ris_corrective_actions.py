"""Corrective Actions persistence — ris_corrective_actions.

QA-11: Track corrective actions arising from QA incidents. Each action
has an assignee, due date, status, and optional link to an incident.
Escalation logic lives in the API layer (due_date + status = overdue →
notification fan-out). The table is self-contained; no foreign key to
an incidents table — the incident_id is a free-text reference so the
schema stays decoupled.
"""
from pypika.dialects import PostgreSQLQuery as Query_
from datetime import datetime, timezone

from db.table import Table
from db.conn import get_tenant_slug


class RisCorrectiveActions(Table):
    name = 'ris_corrective_actions'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_corrective_actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            assignee_id TEXT NOT NULL DEFAULT '',
            incident_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled')),
            priority TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            due_date TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_corrective_actions_status
            ON ris_corrective_actions (status, due_date)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_corrective_actions_assignee
            ON ris_corrective_actions (assignee_id)
        """)
        await self._ensure_tenant()

    async def _ensure_tenant(self):
        await self.conn.execute(
            "ALTER TABLE ris_corrective_actions "
            "ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'"
        )

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def get(self, action_id):
        q = self.query().select('*').where(self.table.id == action_id)
        return await self.fetchone(q)

    async def update(self, action_id, data):
        data = dict(data)
        if data.get('status') == 'completed' and not data.get('completed_at'):
            data['completed_at'] = datetime.now(timezone.utc)
        q = Query_.update(self.table).where(self.table.id == action_id)
        for col, val in data.items():
            q = q.set(self.table[col], val)
        q = q.returning('*')
        return await self.fetchone(q)

    async def delete(self, action_id):
        q = self.query().delete().where(self.table.id == action_id)
        return await self.execute(q)

    async def list_all(self, status=None):
        if status:
            q = (self.query().select('*')
                 .where(self.table.status == status)
                 .orderby(self.table.due_date))
        else:
            q = self.query().select('*').orderby(self.table.due_date)
        return await self.fetch(q)

    async def list_overdue(self):
        """Return open/in_progress actions past their due date."""
        rows = await self.fetch(
            self.query().select('*')
            .where(self.table.status.isin(['open', 'in_progress']))
            .where(self.table.due_date < datetime.now(timezone.utc))
            .orderby(self.table.due_date)
        )
        return rows
