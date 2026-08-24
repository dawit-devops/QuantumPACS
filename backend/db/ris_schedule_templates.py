"""RIS schedule templates (S-05) — ris_schedule_templates.

Templates are named collections of weekly availability windows that a
scheduler can apply to any resource, avoiding repetitive per-day entry.
Each template stores its slots as a JSON array; apply reads the slots
and batch-inserts ris_resource_schedules rows for the target resource.
"""
from datetime import datetime, timezone

from db.conn import get_tenant_slug
from db.table import Table


class RisScheduleTemplates(Table):
    name = 'ris_schedule_templates'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_schedule_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            slots JSONB NOT NULL DEFAULT '[]',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_ris_template_name UNIQUE (tenant_id, name)
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_template_tenant
            ON ris_schedule_templates (tenant_id)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def get(self, template_id):
        q = self.query().select('*').where(self.table.id == template_id)
        return await self.fetchone(q)

    async def list_for_tenant(self, tenant_id=None):
        tid = tenant_id or get_tenant_slug() or 'default'
        q = self.query().select('*').where(self.table.tenant_id == tid)
        q = q.orderby(self.table.name)
        return await self.fetch(q)

    async def delete(self, template_id):
        q = self.table.delete().where(self.table.id == template_id)
        return await self.exec(q)
