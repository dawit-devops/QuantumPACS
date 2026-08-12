from db.conn import get_tenant_slug
from db.table import Table
from pypika.pseudocolumns import PseudoColumn


class Series(Table):
    name = 'series'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS series (
            id SERIAL PRIMARY KEY,
            study_id INTEGER NOT NULL REFERENCES studies(id),
            number TEXT NOT NULL,
            modality TEXT NOT NULL,
            description TEXT,
            series_instance_uid TEXT,
            tenant_id TEXT,
            UNIQUE(study_id, number)
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS series_number ON series(number);
        """)
        # Parity with migration 017.
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_series_series_instance_uid
        ON series(series_instance_uid) WHERE series_instance_uid IS NOT NULL
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_series_tenant ON series(tenant_id);
        """)

    async def insert_or_select(self, data):
        q = self.insert().columns(
            'study_id', 'number', 'modality', 'description', 'series_instance_uid',
            'tenant_id',
        ).insert((
            data['study_db_id'], data['series_number'], data.get('modality', ''),
            data.get('series_description', ''), data.get('series_instance_uid', ''),
            get_tenant_slug() or 'default',
        ),        ).on_conflict(
            'study_id', 'number'
        ).do_update(
            self.table.description, PseudoColumn('EXCLUDED.description')
        ).returning('id')

        sid = await self.fetchval(q)
        return {'id': sid}
