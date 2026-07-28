from db.table import Table


class RoutingRule(Table):
    name = 'routing_rules'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS routing_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            conditions JSONB NOT NULL DEFAULT '{}',
            destination TEXT NOT NULL,
            priority INT NOT NULL DEFAULT 0,
            enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("CREATE INDEX IF NOT EXISTS ix_routing_rules_enabled ON routing_rules(enabled)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_routing_rules_priority ON routing_rules(priority)")

    async def create(self, data):
        cols = ['name', 'description', 'conditions', 'destination', 'priority', 'enabled']
        vals = [
            data['name'],
            data.get('description', ''),
            data.get('conditions', '{}'),
            data['destination'],
            int(data.get('priority', 0)),
            bool(data.get('enabled', True)),
        ]
        if 'tenant_id' in data:
            cols.append('tenant_id')
            vals.append(data['tenant_id'])
        q = self.insert().columns(*cols).insert(tuple(vals),).returning('id')
        return {'id': await self.fetchval(q)}

    async def update(self, rule_id, data):
        cols = ['name', 'description', 'conditions', 'destination', 'priority', 'enabled']
        if 'tenant_id' in data:
            cols.append('tenant_id')
        sets = []
        for col in cols:
            if col in data:
                sets.append(f"{col} = ${len(sets) + 2}")
        if not sets:
            return False
        sets.append("updated_at = now()")
        vals = [data[c] for c in cols if c in data]
        vals.append(rule_id)
        q = f"UPDATE routing_rules SET {', '.join(sets)} WHERE id = ${len(vals)}"
        await self.conn.execute(q, *vals)
        return True

    async def list_all(self, enabled_only=False, tenant_id=None):
        q = self.select(self.table.star)
        if enabled_only:
            q = q.where(self.table.enabled == True)
        if tenant_id:
            q = q.where(self.table.tenant_id == tenant_id)
        q = q.orderby(self.table.priority)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def count(self, enabled_only=False, tenant_id=None):
        q = "SELECT COUNT(*) FROM routing_rules"
        where = []
        vals = []
        if enabled_only:
            where.append("enabled = true")
        if tenant_id:
            where.append(f"tenant_id = ${len(vals) + 1}")
            vals.append(tenant_id)
        if where:
            q += " WHERE " + " AND ".join(where)
        return await self.fetchval(q, *vals)

    async def list_paginated(self, page=1, per_page=50, enabled_only=False, tenant_id=None):
        q = self.select(self.table.star)
        if enabled_only:
            q = q.where(self.table.enabled == True)
        if tenant_id:
            q = q.where(self.table.tenant_id == tenant_id)
        q = q.orderby(self.table.priority)
        q = q.limit(per_page).offset((page - 1) * per_page)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def get_by_id(self, rule_id):
        q = self.select(self.table.star).where(self.table.id == rule_id)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def delete(self, rule_id):
        q = self.delete(using='routing_rules').where(self.table.id == rule_id)
        await self.exec(q)
