from unittest.mock import AsyncMock, patch

import pytest

from db.tenants import Tenants
from db.tenant_provisioner import TenantProvisioner


class TestTenantSoftDelete:
    @pytest.mark.asyncio
    async def test_soft_delete_marks_decommissioned(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'tenant-1', 'slug': 'tenant-1', 'name': 'T1',
            'db_password': 'secret',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        t = Tenants(conn=conn)
        await t.delete('tenant-1')
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert 'decommissioned' in sql
        assert 'decommissioned_at' in sql
        assert 'DELETE' not in sql

    @pytest.mark.asyncio
    async def test_get_all_filters_decommissioned_by_default(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': '1', 'slug': 'active-tenant', 'status': 'active',
             'created_at': '', 'updated_at': ''},
        ]
        t = Tenants(conn=conn)
        await t.get_all()
        sql = conn.fetch.call_args[0][0]
        assert "decommissioned" in sql
        assert "status" in sql

    @pytest.mark.asyncio
    async def test_get_all_includes_decommissioned_with_flag(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': '1', 'slug': 'decom-tenant', 'status': 'decommissioned',
             'created_at': '', 'updated_at': ''},
        ]
        t = Tenants(conn=conn)
        await t.get_all(include_decommissioned=True)
        sql = conn.fetch.call_args[0][0]
        assert "status" not in sql.lower() or "decommissioned" not in sql

    @pytest.mark.asyncio
    async def test_hard_delete_removes_row(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'id': '1', 'slug': 'to-delete', 'db_name': 'test'}
        t = Tenants(conn=conn)
        await t.hard_delete('to-delete')
        sql = conn.execute.call_args[0][0]
        assert 'DELETE' in sql
        assert 'to-delete' in sql


class TestCreateInitialAdmin:
    @pytest.mark.asyncio
    async def test_create_initial_admin_creates_user_with_correct_role(self):
        conn_mock = AsyncMock()
        conn_mock.fetchval.return_value = 42
        with patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)):
            password = await TenantProvisioner.create_initial_admin(
                db_name='test_tenant_db', slug='test-clinic',
                admin_email='admin@test.com',
            )
            assert password is not None
            assert len(password) > 0
            insert_sql = conn_mock.execute.call_args[0][0]
            assert 'INSERT INTO users' in insert_sql
            assert conn_mock.fetchval.called
            role_sql = conn_mock.fetchval.call_args[0][0]
            assert 'tenant_admin' in role_sql
            exec_args = conn_mock.execute.call_args[0]
            assert 'admin-test-clinic' in str(exec_args[1])

    @pytest.mark.asyncio
    async def test_create_initial_admin_raises_if_role_missing(self):
        conn_mock = AsyncMock()
        conn_mock.fetchval.return_value = None
        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            pytest.raises(Exception) as exc,
        ):
            await TenantProvisioner.create_initial_admin(
                db_name='test_db', slug='clinic', admin_email='a@b.com',
            )
        assert 'tenant_admin' in str(exc.value)


class TestProvisionReturnsPassword:
    @pytest.mark.asyncio
    async def test_provision_returns_dict_with_password(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = None
        conn_mock.fetchval.return_value = 42

        admin_password = 'test-generated-password'

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
            patch('db.tenant_provisioner.TenantProvisioner.create_initial_admin',
                  new=AsyncMock(return_value=admin_password)),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            result = await TenantProvisioner.provision(
                slug='test-clinic', name='Test Clinic',
                admin_email='admin@test.clinic',
            )
            assert isinstance(result, dict)
            assert 'tenant_id' in result
            assert result['tenant_id'] == 42
            assert 'admin_password' in result
            assert result['admin_password'] == admin_password
