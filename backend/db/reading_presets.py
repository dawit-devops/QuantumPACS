"""Per-user reading presets for the R12 Staff Radiologist workflow (FR-R12-15).

A radiologist saves window/level and viewport-layout presets per modality and
reuses them across sessions and workstations. Presets are owned by a single
user (users.id is a bigint).

Two preset types:
- window_level: { window_center, window_width, invert } — applied to viewports
- layout: { rows, cols } — companion-viewport grid (1x1, 1x2, 2x2)
"""
from datetime import datetime, timezone

from db.table import Table


class ReadingPresets(Table):
    name = 'reading_presets'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS reading_presets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id BIGINT NOT NULL,
            preset_type TEXT NOT NULL
                CHECK (preset_type IN ('window_level', 'layout')),
            modality TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            config JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_reading_presets_user_type_modality_name
            ON reading_presets(user_id, preset_type, modality, name)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_reading_presets_user
            ON reading_presets(user_id, preset_type, modality)
        """)

    async def list_for_user(self, user_id, preset_type=None, modality=None):
        where = ["user_id = $1"]
        params = [int(user_id)]
        if preset_type:
            where.append(f"preset_type = ${len(params) + 1}")
            params.append(preset_type)
        if modality:
            where.append(f"modality = ${len(params) + 1}")
            params.append(modality)
        rows = await self.conn.fetch(
            f"SELECT * FROM reading_presets WHERE {' AND '.join(where)} "
            f"ORDER BY is_default DESC, name",
            *params,
        )
        return [dict(r) for r in rows]

    async def get(self, preset_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM reading_presets WHERE id = $1", preset_id,
        )
        return dict(row) if row else None

    async def create(self, user_id, preset_type, modality, name, config, is_default):
        import json as _json

        now = datetime.now(timezone.utc)
        if is_default:
            # Only one default preset per user/type/modality.
            await self.conn.execute(
                "UPDATE reading_presets SET is_default = FALSE "
                "WHERE user_id = $1 AND preset_type = $2 AND modality = $3",
                int(user_id), preset_type, modality,
            )
        q = self.insert().columns(
            'user_id', 'preset_type', 'modality', 'name', 'config',
            'is_default', 'created_at', 'updated_at',
        ).insert((
            int(user_id), preset_type, modality, name,
            _json.dumps(config), is_default, now, now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create reading preset')
        return await self.get(row['id'])

    async def update(self, preset_id, config=None, name=None, is_default=None,
                     modality=None):
        import json as _json

        fields = ['updated_at']
        values = [datetime.now(timezone.utc)]
        for col, val in (('config', config), ('name', name),
                         ('is_default', is_default), ('modality', modality)):
            if val is None:
                continue
            fields.append(col)
            values.append(_json.dumps(val) if col == 'config' else val)
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        await self.conn.execute(
            f"UPDATE reading_presets SET {set_clause} WHERE id = $1",
            preset_id, *values,
        )
        return await self.get(preset_id)

    async def delete(self, preset_id):
        await self.conn.execute(
            "DELETE FROM reading_presets WHERE id = $1", preset_id,
        )
