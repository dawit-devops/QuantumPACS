"""Durable platform-wide state (maintenance mode and similar flags).

Values are JSONB; the in-process mirror (api.admin._maintenance_state) is
the fast path for the request gate and this module is the source of truth
loaded at startup and on toggle. Never stores secrets.
"""

import json


class PlatformState:
    def __init__(self, conn=None):
        self.conn = conn

    async def get(self, key, default=None):
        row = await self.conn.fetchrow(
            'SELECT value FROM platform_state WHERE key = $1', key,
        )
        if not row:
            return default
        return row['value']

    async def set(self, key, value):
        await self.conn.execute(
            'INSERT INTO platform_state (key, value, updated_at) '
            'VALUES ($1, $2, now()) '
            'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, '
            'updated_at = now()',
            key, json.dumps(value),
        )

    async def delete(self, key):
        await self.conn.execute(
            'DELETE FROM platform_state WHERE key = $1', key,
        )
