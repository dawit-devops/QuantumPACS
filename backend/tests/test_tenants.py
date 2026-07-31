from unittest.mock import AsyncMock, patch

import pytest

from db.tenants import Tenants, TenantConnectionPool


class TestTenants:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': '1', 'name': 'Hospital A', 'slug': 'hospital-a',
             'db_name': 'hosp_a', 'created_at': '2026-01-01', 'updated_at': '2026-01-01'},
            {'id': '2', 'name': 'Hospital B', 'slug': 'hospital-b',
             'db_name': 'hosp_b', 'created_at': '2026-01-02', 'updated_at': '2026-01-02'},
        ]
        t = Tenants(conn=conn)
        result = await t.get_all()
        assert len(result) == 2
        assert result[0]['name'] == 'Hospital A'

    @pytest.mark.asyncio
    async def test_get_returns_tenant(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'abc-123', 'name': 'Hospital A', 'slug': 'hospital-a',
            'db_name': 'hosp_a', 'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        t = Tenants(conn=conn)
        result = await t.get('abc-123')
        assert result['slug'] == 'hospital-a'

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        t = Tenants(conn=conn)
        result = await t.get('missing-id')
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug_finds_tenant(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'abc-123', 'name': 'Hospital A', 'slug': 'hospital-a',
            'db_name': 'hosp_a',
        }
        t = Tenants(conn=conn)
        result = await t.get_by_slug('hospital-a')
        assert result['id'] == 'abc-123'
        assert result['db_name'] == 'hosp_a'

    @pytest.mark.asyncio
    async def test_create_returns_id(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id-456'
        t = Tenants(conn=conn)
        tenant_id = await t.create(
            name='Hospital A', slug='hospital-a',
            db_name='hosp_a',
        )
        assert tenant_id == 'new-id-456'
        sql = conn.fetchval.call_args[0][0]
        assert 'INSERT INTO' in sql

    @pytest.mark.asyncio
    async def test_create_defaults_db_name_to_slug(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id-789'
        t = Tenants(conn=conn)
        await t.create(name='My Clinic', slug='my-clinic')
        sql = conn.fetchval.call_args[0][0]
        assert 'my_clinic' in sql

    @pytest.mark.asyncio
    async def test_patch_updates_fields(self):
        conn = AsyncMock()
        t = Tenants(conn=conn)
        await t.patch('tenant-1', {'name': 'Updated Name', 'db_host': '10.0.0.1'})
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert 'updated_at' in sql

    @pytest.mark.asyncio
    async def test_delete_soft_deletes_tenant(self):
        conn = AsyncMock()
        t = Tenants(conn=conn)
        await t.delete('tenant-1')
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert 'decommissioned' in sql

    @pytest.mark.asyncio
    async def test_to_json_removes_db_password(self):
        data = {
            'id': '1', 'name': 'Test', 'slug': 'test',
            'db_password': 'secret',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        result = Tenants.to_json(data)
        assert 'db_password' not in result
        assert result['name'] == 'Test'


class TestTenantConnectionPool:
    @pytest.mark.asyncio
    async def test_get_creates_new_pool(self):
        pool_mock = AsyncMock()
        with patch('asyncpg.create_pool', new=AsyncMock(return_value=pool_mock)):
            TenantConnectionPool._pools.clear()
            TenantConnectionPool._last_used.clear()
            pool = await TenantConnectionPool.get(
                'test-tenant',
                tenant_info={'db_name': 'test_db', 'db_host': '127.0.0.1'},
            )
            assert pool is pool_mock
            assert 'test-tenant' in TenantConnectionPool._pools

    @pytest.mark.asyncio
    async def test_get_returns_existing_pool(self):
        existing = AsyncMock()
        TenantConnectionPool._pools.clear()
        TenantConnectionPool._last_used.clear()
        TenantConnectionPool._pools['cached-tenant'] = existing

        pool = await TenantConnectionPool.get('cached-tenant')
        assert pool is existing

    @pytest.mark.asyncio
    async def test_get_raises_without_info(self):
        TenantConnectionPool._pools.clear()
        TenantConnectionPool._last_used.clear()
        with pytest.raises(KeyError):
            await TenantConnectionPool.get('unknown-tenant')

    @pytest.mark.asyncio
    async def test_close_removes_pool(self):
        pool_mock = AsyncMock()
        TenantConnectionPool._pools['to-close'] = pool_mock
        TenantConnectionPool._last_used['to-close'] = 1.0

        await TenantConnectionPool.close('to-close')

        assert 'to-close' not in TenantConnectionPool._pools
        pool_mock.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_all_clears_all(self):
        TenantConnectionPool._pools.clear()
        TenantConnectionPool._last_used.clear()
        p1, p2 = AsyncMock(), AsyncMock()
        TenantConnectionPool._pools['a'] = p1
        TenantConnectionPool._pools['b'] = p2
        TenantConnectionPool._last_used['a'] = 1.0
        TenantConnectionPool._last_used['b'] = 2.0

        await TenantConnectionPool.close_all()

        assert len(TenantConnectionPool._pools) == 0
        p1.close.assert_awaited_once()
        p2.close.assert_awaited_once()
