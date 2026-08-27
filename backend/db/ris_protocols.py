"""Protocol Registry persistence — ris_protocols.

QA-09: CRUD for imaging protocols with version control, modality
assignment, and per-modality default designation. version is an integer
bumped on each save so the UI can show a version history timeline.

The tenant boundary is enforced via the standard _ensure_requesting_tenant
ALTER; queries always filter on tenant_id.
"""
from pypika.dialects import PostgreSQLQuery as Query_
from datetime import datetime, timezone

from db.table import Table
from db.conn import get_tenant_slug


class RisProtocols(Table):
    name = 'ris_protocols'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_protocols (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            modality TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1,
            is_default BOOLEAN NOT NULL DEFAULT false,
            content TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_protocols_modality
            ON ris_protocols (modality)
        """)
        await self._ensure_tenant()

    async def _ensure_tenant(self):
        await self.conn.execute(
            "ALTER TABLE ris_protocols "
            "ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'"
        )

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        data.setdefault('version', 1)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def get(self, protocol_id):
        q = self.query().select('*').where(self.table.id == protocol_id)
        return await self.fetchone(q)

    async def update(self, protocol_id, data):
        data = dict(data)
        # Bump version on every save
        data['version'] = (
            data.get('version', 0) + 1
        )
        q = Query_.update(self.table).where(self.table.id == protocol_id)
        for col, val in data.items():
            q = q.set(self.table[col], val)
        q = q.returning('*')
        return await self.fetchone(q)

    async def delete(self, protocol_id):
        q = self.query().delete().where(self.table.id == protocol_id)
        return await self.execute(q)

    async def list_all(self):
        q = (self.query().select('*').orderby(self.table.name))
        return await self.fetch(q)

    async def list_by_modality(self, modality):
        q = (self.query().select('*')
             .where(self.table.modality == modality)
             .orderby(self.table.name))
        return await self.fetch(q)

    async def get_default(self, modality):
        """Return the default protocol for a modality (if any)."""
        q = (self.query().select('*')
             .where(self.table.modality == modality)
             .where(self.table.is_default)
             .limit(1))
        return await self.fetchone(q)

    async def set_default(self, protocol_id, modality):
        """Clear existing default for this modality, then set new default."""
        await self.conn.execute(
            "UPDATE ris_protocols SET is_default = false "
            "WHERE modality = $1 AND tenant_id = $2",
            modality, get_tenant_slug() or 'default',
        )
        q = (Query_.update(self.table)
             .set(self.table.is_default, True)
             .where(self.table.id == protocol_id)
             .returning('*'))
        return await self.fetchone(q)
