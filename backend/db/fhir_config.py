from db.table import Table


class FhirConfig(Table):
    name = 'fhir_config'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS fhir_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)

    async def get_all(self) -> dict:
        rows = await self.fetch(self.select('key', 'value'))
        return {r['key']: r['value'] for r in rows}

    async def set(self, key: str, value: str):
        await self.exec(
            self.insert().columns('key', 'value').insert((key, value)).on_conflict('key').do_update('value', value)
        )

    async def set_many(self, kv: dict):
        for k, v in kv.items():
            await self.set(k, v)
