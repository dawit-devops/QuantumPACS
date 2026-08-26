"""RIS waitlist persistence — S-08 waitlist management."""

from datetime import datetime, timezone

from db.table import Table


class RisWaitlist(Table):
    name = 'ris_waitlist'

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('created_at', now)
        data.setdefault('status', 'WAITING')
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def list_for_tenant(self, tenant_id, resource_id=None, status=None):
        q = self.select('*').where(self.table.tenant_id == tenant_id)
        if resource_id:
            q = q.where(self.table.resource_id == resource_id)
        if status:
            q = q.where(self.table.status == status)
        q = q.orderby(
            self.table.priority == 'STAT', self.table.priority == 'URGENT',
            self.table.created_at,
        )
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def get(self, entry_id):
        q = self.select('*').where(self.table.id == entry_id)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def update_status(self, entry_id, status):
        q = self.update().set(self.table.status, status)
        if status == 'NOTIFIED':
            q = q.set(self.table.notified_at, datetime.now(timezone.utc))
        q = q.where(self.table.id == entry_id).returning('*')
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def delete(self, entry_id):
        q = self.query().from_(self.table).delete().where(self.table.id == entry_id)
        await self.exec(q)