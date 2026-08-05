from pypika import Order

from db.table import Table


class Webhook(Table):
    name = 'webhooks'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT[] NOT NULL DEFAULT '{}',
            secret TEXT DEFAULT '',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            retry_count INTEGER NOT NULL DEFAULT 3,
            timeout_ms INTEGER NOT NULL DEFAULT 5000,
            last_triggered_at TIMESTAMPTZ,
            last_status_code INTEGER,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)

    async def get_all(self):
        rows = await self.fetch(
            self.select('id', 'name', 'url', 'events', 'active',
                        'retry_count', 'timeout_ms',
                        'last_triggered_at', 'last_status_code',
                        'last_error', 'created_at')
            .orderby('created_at', order=Order.desc)
        )
        return [dict(r) for r in rows]

    async def get_by_id(self, wh_id):
        row = await self.fetchone(self.select('*').where(self.table.id == wh_id))
        return dict(row) if row else None

    async def create(self, data):
        q = self.insert().columns(
            'name', 'url', 'events', 'secret', 'active',
            'retry_count', 'timeout_ms',
        ).insert((
            data['name'], data['url'],
            data.get('events', []),
            data.get('secret', ''),
            data.get('active', True),
            int(data.get('retry_count', 3)),
            int(data.get('timeout_ms', 5000)),
        )).returning('id')
        return await self.fetchval(q)

    async def update_webhook(self, wh_id, data):
        sets = []
        vals = []
        idx = 1
        for col in ('name', 'url', 'events', 'secret', 'active', 'retry_count', 'timeout_ms'):
            if col in data:
                sets.append(f'{col} = ${idx}')
                vals.append(data[col])
                idx += 1
        if not sets:
            return
        sets.append('updated_at = now()')
        vals.append(wh_id)
        await self.conn.execute(
            f'UPDATE webhooks SET {", ".join(sets)} WHERE id = ${idx}',
            *vals
        )

    async def delete(self, wh_id):
        await self.exec(
            self.query().delete().where(self.table.id == wh_id)
        )

    async def record_trigger(self, wh_id: str, status_code: int, error: str = ''):
        await self.conn.execute(
            'UPDATE webhooks SET last_triggered_at = now(), last_status_code = $1, last_error = $2 WHERE id = $3',
            status_code, error, wh_id
        )
