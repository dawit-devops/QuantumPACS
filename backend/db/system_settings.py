"""Whitelisted platform-config overrides (super_admin review P2-3).

The Settings page reads/writes these keys; at startup the backend merges
them over config.py defaults so the platform admin can tune runtime-safe
keys without editing YAML. Secrets are never stored here — the API layer
enforces the whitelist.
"""

import json


class SystemSettings:
    def __init__(self, conn=None):
        self.conn = conn

    async def get_all(self):
        rows = await self.conn.fetch(
            'SELECT key, value FROM system_settings',
        )
        return {r['key']: r['value'] for r in rows}

    async def set(self, key, value):
        await self.conn.execute(
            'INSERT INTO system_settings (key, value, updated_at) '
            'VALUES ($1, $2, now()) '
            'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, '
            'updated_at = now()',
            key, json.dumps(value),
        )
