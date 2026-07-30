import uuid
import secrets

from pypika import Order

from db.table import Table


class FhirClient(Table):
    name = 'fhir_clients'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS fhir_clients (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            client_id TEXT NOT NULL UNIQUE,
            client_secret TEXT NOT NULL,
            redirect_uris TEXT DEFAULT '',
            grant_type TEXT NOT NULL DEFAULT 'client_credentials',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            last_used TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """)

    async def get_all(self):
        rows = await self.fetch(
            self.select(
                'id', 'name', 'description', 'client_id', 'redirect_uris',
                'grant_type', 'active', 'last_used', 'created_at'
            ).orderby('created_at', order=Order.desc)
        )
        return [dict(r) for r in rows]

    async def get_by_id(self, client_id: str):
        row = await self.fetchone(self.select('*').where(self.table.id == client_id))
        return dict(row) if row else None

    async def create(self, name: str, description: str, redirect_uris: str, grant_type: str) -> dict:
        raw_id = str(uuid.uuid4())
        client_id = 'qp_' + raw_id[:12]
        client_secret = 'qps_' + secrets.token_urlsafe(32)
        await self.exec(
            self.insert().columns(
                'name', 'description', 'client_id', 'client_secret',
                'redirect_uris', 'grant_type'
            ).insert((name, description, client_id, client_secret, redirect_uris, grant_type))
        )
        return {
            'id': raw_id,
            'name': name,
            'description': description,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uris': redirect_uris,
            'grant_type': grant_type,
        }

    async def update_client(self, client_id: str, data: dict):
        sets = []
        vals = []
        idx = 1
        for col in ('name', 'description', 'redirect_uris', 'grant_type', 'active'):
            if col in data:
                sets.append(f'{col} = ${idx}')
                vals.append(data[col])
                idx += 1
        if not sets:
            return
        sets.append(f'updated_at = now()')
        vals.append(client_id)
        await self.conn.execute(
            f'UPDATE fhir_clients SET {", ".join(sets)} WHERE id = ${idx}',
            *vals
        )

    async def deactivate(self, client_id: str):
        await self.exec(
            self.update().set('active', False).set('updated_at', self.conn.execute('now()')).where(
                self.table.id == client_id
            )
        )

    async def delete(self, client_id: str):
        await self.exec(
            self.query().delete().where(self.table.id == client_id)
        )
