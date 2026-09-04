"""RIS resource persistence (S4-06) — ris_resources + ris_resource_schedules.

Resources are the schedulable capacity: rooms, modalities, technologists.
Schedules define weekly availability windows per resource. Tenant isolation
follows the S3 pattern (tenant_id tag column + per-tenant pools), and a
resource name is unique per tenant so cross-tenant feeds never collide.
"""
from datetime import datetime, timezone

from pypika import Order

from db.conn import get_tenant_slug
from db.table import Table


class RisResources(Table):
    name = 'ris_resources'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL
                CHECK (resource_type IN ('ROOM', 'MODALITY', 'TECH')),
            modality TEXT DEFAULT '',
            location TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'INACTIVE')),
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_ris_resource_name UNIQUE (tenant_id, name)
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_resources_tenant_type
            ON ris_resources (tenant_id, resource_type)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_resources_modality
            ON ris_resources (modality)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def list_for_tenant(self, resource_type=None, modality=None, include_inactive=False):
        q = self.query().select('*').where(
            self.table.tenant_id == (get_tenant_slug() or 'default')
        )
        if resource_type:
            q = q.where(self.table.resource_type == resource_type)
        if modality:
            q = q.where(self.table.modality == modality)
        if not include_inactive:
            q = q.where(self.table.status == 'ACTIVE')
        q = q.orderby(self.table.name, order=Order.asc)
        return await self.fetch(q)

    async def get(self, resource_id):
        q = self.query().select('*').where(self.table.id == resource_id)
        return await self.fetchone(q)


class RisResourceSchedules(Table):
    name = 'ris_resource_schedules'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_resource_schedules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            resource_id UUID NOT NULL REFERENCES ris_resources(id) ON DELETE CASCADE,
            day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT chk_ris_schedule_end_after_start CHECK (end_time > start_time)
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_schedules_resource
            ON ris_resource_schedules (resource_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_schedules_tenant_day
            ON ris_resource_schedules (tenant_id, day_of_week)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def for_resource(self, resource_id):
        q = self.query().select('*').where(self.table.resource_id == resource_id)
        q = q.orderby(self.table.day_of_week)
        return await self.fetch(q)

    async def delete(self, schedule_id):
        q = self.table.delete().where(self.table.id == schedule_id)
        return await self.exec(q)