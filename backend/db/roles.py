import json

from pypika.dialects import PostgreSQLQuery as Query_

from db.table import Table


NAME_BY_SLUG = {
    'super_admin': 'Super Admin',
    'tenant_admin': 'Tenant Admin',
    'technologist': 'Technologist',
    'radiologist': 'Radiologist',
    'physician': 'Physician',
    'cashier': 'Cashier',
    'teleradiologist': 'Teleradiologist',
    'receptionist': 'Receptionist',
    'referring_physician': 'Referring Physician',
    'pacs_admin': 'PACS Administrator',
    'resident': 'Resident',
    'care_coordinator': 'Care Coordinator',
    'emr_admin': 'EMR Admin',
    'patient': 'Patient',
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
        q = f"""
            SELECT r.*, COUNT(u.id)::int AS user_count
            FROM {self.name} r
            LEFT JOIN users u ON u.role_id = r.id
            GROUP BY r.id
            ORDER BY r.name
        """
        data = await self.conn.fetch(q)
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
        from api.permissions import (
            BUILT_IN_ROLES,
            IMMUTABLE_ROLE_SLUGS,
        )

        for slug, permissions in BUILT_IN_ROLES.items():
            name = NAME_BY_SLUG.get(slug, slug.replace('_', ' ').title())
            perms_json = json.dumps(permissions)
            if slug in IMMUTABLE_ROLE_SLUGS:
                # Immutable anchors get the full upsert: drift would silently
                # widen or shrink platform/tenant/patient administration.
                await self.conn.execute(
                    'INSERT INTO roles (slug, name, permissions, built_in, created_at, updated_at) '
                    'VALUES ($1, $2, $3::jsonb, TRUE, now(), now()) '
                    'ON CONFLICT (slug) DO UPDATE SET '
                    'name = EXCLUDED.name, permissions = EXCLUDED.permissions, '
                    'built_in = TRUE, updated_at = now()',
                    slug, name, perms_json,
                )
            else:
                # Editable built-ins (facility-edited clinical/operational
                # slugs, incl. the platform-only teleradiologist) are seeded
                # only when absent: an upsert here would wipe tenant-admin /
                # platform-admin edits on every boot. But a stored set that is
                # a strict SUPERSET of the canonical grants is drift, not a
                # facility edit (technologist review P0-1: migration 048's
                # trim was overwritten by an over-granted set) — reconcile
                # those to canonical so a drifted DB converges without
                # clobbering legitimate edits (a subset/other shape).
                row = await self.conn.fetchrow(
                    'SELECT permissions FROM roles WHERE slug = $1', slug,
                )
                stored = set(row['permissions']) if row and row['permissions'] else set()
                canonical = set(permissions)
                if not row:
                    await self.conn.execute(
                        'INSERT INTO roles (slug, name, permissions, built_in, created_at, updated_at) '
                        'VALUES ($1, $2, $3::jsonb, TRUE, now(), now())',
                        slug, name, perms_json,
                    )
                elif stored != canonical and stored > canonical:
                    # Superset drift: bring the row back to canonical.
                    await self.conn.execute(
                        'UPDATE roles SET permissions = $2::jsonb, updated_at = now() '
                        'WHERE slug = $1',
                        slug, perms_json,
                    )
