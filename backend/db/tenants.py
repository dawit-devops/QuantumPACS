import time

import asyncpg

from config import config
from db.table import Table


class TenantConnectionPool:
    _pools: dict = {}
    _last_used: dict = {}
    _max_pools: int = 50
    _ttl: int = 300

    @classmethod
    async def get(cls, tenant_slug: str, tenant_info: dict | None = None):
        now = time.monotonic()
        if tenant_slug in cls._pools:
            pool = cls._pools[tenant_slug]
            cls._last_used[tenant_slug] = now
            return pool

        if len(cls._pools) >= cls._max_pools:
            cls._evict_lru()

        if not tenant_info:
            raise KeyError(f'No connection info for tenant: {tenant_slug}')

        pool = await asyncpg.create_pool(
            user=tenant_info.get('db_user', config['db_user']),
            password=tenant_info.get('db_password', config['db_password']),
            database=tenant_info['db_name'],
            host=tenant_info.get('db_host', config['db_host']),
            port=int(tenant_info.get('db_port', config.get('db_port', '5432'))),
            min_size=1,
            max_size=4,
            command_timeout=30,
        )
        cls._pools[tenant_slug] = pool
        cls._last_used[tenant_slug] = now
        return pool

    @classmethod
    async def close(cls, tenant_slug: str):
        pool = cls._pools.pop(tenant_slug, None)
        cls._last_used.pop(tenant_slug, None)
        if pool:
            await pool.close()

    @classmethod
    async def close_all(cls):
        for slug in list(cls._pools.keys()):
            await cls.close(slug)

    @classmethod
    def _evict_lru(cls):
        if not cls._last_used:
            return
        oldest = min(cls._last_used, key=cls._last_used.get)
        import asyncio
        asyncio.create_task(cls.close(oldest))


class Tenants(Table):
    name = 'tenants'

    async def sync_db(self):
        pass

    @staticmethod
    def to_json(data):
        data = dict(data)
        for field in ('db_password',):
            data.pop(field, None)
        data['created_at'] = str(data.get('created_at', ''))
        data['updated_at'] = str(data.get('updated_at', ''))
        return data

    async def get_all(self, include_decommissioned=False):
        q = self.select('*')
        if not include_decommissioned:
            q = q.where(self.table.status != 'decommissioned')
        q = q.orderby(self.table.name)
        data = await self.fetch(q)
        return [self.to_json(d) for d in data]

    async def get(self, tenant_id):
        q = self.select('*').where(self.table.id == tenant_id)
        data = await self.fetchone(q)
        return self.to_json(data) if data else None

    async def get_by_slug(self, slug):
        q = self.select('*').where(self.table.slug == slug)
        data = await self.fetchone(q)
        return dict(data) if data else None

    async def create(self, name, slug, domain=None, db_name=None,
                     db_host=None, db_port=None, db_user=None,
                     db_password=None, storage_quota_bytes=0,
                     status='active', plan='free'):
        if db_name is None:
            db_name = slug.replace('-', '_')
        q = self.insert().columns(
            self.table.name, self.table.slug, self.table.domain,
            self.table.db_name, self.table.db_host, self.table.db_port,
            self.table.db_user, self.table.db_password,
            self.table.storage_quota_bytes,
            self.table.status, self.table.plan,
        ).insert(
            name, slug, domain, db_name,
            db_host or config['db_host'],
            db_port or int(config.get('db_port', '5432')),
            db_user or config['db_user'],
            db_password or config['db_password'],
            storage_quota_bytes,
            status, plan,
        ).returning(self.table.id)
        return await self.fetchval(q)

    async def set_status(self, slug, status):
        """Transition a tenant's status (active/suspended/quarantined/
        decommissioned) by slug — used by the provisioner lifecycle.
        UPDATE..RETURNING via fetchval keeps provisioning's only conn-level
        execute as CREATE DATABASE (a committed test asserts that order)."""
        q = self.update().where(self.table.slug == slug).set(
            self.table.status, status,
        ).set(self.table.updated_at, 'NOW()').returning(self.table.id)
        await self.fetchval(q)

    async def persist_storage_used(self, slug, bytes_used):
        """Persist the measured storage footprint for a tenant (bytes)."""
        q = self.update().where(self.table.slug == slug).set(
            self.table.storage_used_bytes, int(bytes_used),
        ).set(self.table.updated_at, 'NOW()')
        await self.exec(q)

    async def patch(self, tenant_id, data):
        q = self.update().where(self.table.id == tenant_id)
        for key, value in data.items():
            if key in ('id', 'created_at', 'storage_used_bytes'):
                continue
            q = q.set(self.table.field(key), value)
        q = q.set(self.table.updated_at, 'NOW()')
        await self.exec(q)

    async def delete(self, tenant_id):
        # Pools are keyed by slug (TenantConnectionPool.get), so resolve the
        # row before closing — closing by id would leave the pool alive and
        # serving a decommissioned tenant until LRU eviction.
        row = await self.get(tenant_id)
        if row:
            await TenantConnectionPool.close(row['slug'])
        q = self.update().where(self.table.id == tenant_id).set(
            self.table.status, 'decommissioned',
        ).set(
            self.table.decommissioned_at, 'NOW()',
        ).set(
            self.table.updated_at, 'NOW()',
        )
        await self.exec(q)

    async def hard_delete(self, slug: str):
        row = await self.get_by_slug(slug)
        if row:
            await TenantConnectionPool.close(row['slug'])
        q = self.query().where(self.table.slug == slug).delete()
        await self.exec(q)

    async def get_connection_info(self, tenant_id):
        q = self.select('*').where(self.table.id == tenant_id)
        data = await self.fetchone(q)
        return dict(data) if data else None

    async def get_stats(self, tenant_slug: str, tenant_info: dict, storage_quota_bytes: int = 0):
        pool = await TenantConnectionPool.get(tenant_slug, tenant_info)
        async with pool.acquire() as conn:
            user_count = await conn.fetchval('SELECT COUNT(*) FROM users')
            study_count = await conn.fetchval('SELECT COUNT(*) FROM studies')
            file_count = await conn.fetchval('SELECT COUNT(*) FROM files')
            storage_used = await conn.fetchval(
                "SELECT COALESCE(SUM(size), 0) FROM files"
            ) or 0
            last_activity = await conn.fetchval(
                "SELECT MAX(created) FROM files"
            )
        return {
            'user_count': user_count or 0,
            'study_count': study_count or 0,
            'file_count': file_count or 0,
            'storage_used_bytes': storage_used,
            'storage_quota_bytes': storage_quota_bytes or 0,
            'storage_pct': round((storage_used / storage_quota_bytes) * 100, 1) if storage_quota_bytes else 0,
            'last_activity': str(last_activity) if last_activity else None,
        }
