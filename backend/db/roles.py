import json

from pypika.dialects import PostgreSQLQuery as Query_

from db.table import Table


NAME_BY_SLUG = {
    'super_admin': 'Super Admin',
    'admin': 'Administrator',
    'tenant_admin': 'Tenant Admin',
    'technologist': 'Technologist',
    'radiologist': 'Radiologist',
    'physician': 'Physician',
    'cashier': 'Cashier',
}


class Roles(Table):
    name = 'roles'

    async def sync_db(self):
        pass

    @staticmethod
    def to_json(data):
        data = dict(data)
        if isinstance(data.get('permissions'), str):
            data['permissions'] = json.loads(data['permissions'])
        return data

    async def get_all(self):
        q = self.select('*').orderby(self.table.name)
        data = await self.fetch(q)
        return [self.to_json(d) for d in data]

    async def get(self, role_id):
        q = self.select('*').where(self.table.id == role_id)
        data = await self.fetchone(q)
        return self.to_json(data) if data else None

    async def get_by_slug(self, slug):
        q = self.select('*').where(self.table.slug == slug)
        data = await self.fetchone(q)
        return self.to_json(data) if data else None

    async def create(self, name, slug, permissions=None, built_in=False, tenant_id=None):
        perms_json = json.dumps(permissions or [])
        q = self.insert().columns(
            self.table.name, self.table.slug, self.table.permissions,
            self.table.built_in, self.table.tenant_id,
        ).insert(name, slug, perms_json, built_in, tenant_id).returning(self.table.id)
        return await self.fetchval(q)

    async def patch(self, role_id, data):
        q = Query_.update(self.table).where(self.table.id == role_id)
        for key, value in data.items():
            if key == 'permissions':
                value = json.dumps(value)
            q = q.set(self.table.field(key), value)
        q = q.set(self.table.updated_at, 'NOW()')
        await self.exec(q)

    async def delete(self, role_id):
        q = self.query().where(self.table.id == role_id).delete()
        await self.exec(q)

    async def seed_built_in_roles(self):
        from api.permissions import BUILT_IN_ROLES

        for slug, permissions in BUILT_IN_ROLES.items():
            name = NAME_BY_SLUG.get(slug, slug.replace('_', ' ').title())
            perms_json = json.dumps(permissions)
            await self.conn.execute(
                'INSERT INTO roles (slug, name, permissions, built_in, created_at, updated_at) '
                'VALUES ($1, $2, $3::jsonb, TRUE, now(), now()) '
                'ON CONFLICT (slug) DO UPDATE SET '
                'name = EXCLUDED.name, permissions = EXCLUDED.permissions, '
                'built_in = TRUE, updated_at = now()',
                slug, name, perms_json,
            )
