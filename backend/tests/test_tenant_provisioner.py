from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.tenant_provisioner import TenantProvisioner, TenantProvisionError


class TestTenantProvisioner:
    @pytest.mark.asyncio
    async def test_create_database(self):
        conn_mock = AsyncMock()
        with patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)):
            await TenantProvisioner.create_database('test_tenant_db')
            sql = conn_mock.execute.call_args[0][0]
            assert 'CREATE DATABASE' in sql
            assert 'test_tenant_db' in sql

    @pytest.mark.asyncio
    async def test_create_database_handles_duplicate(self):
        conn_mock = AsyncMock()
        from asyncpg import DuplicateDatabaseError
        conn_mock.execute.side_effect = DuplicateDatabaseError('already exists')
        with patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)):
            await TenantProvisioner.create_database('existing_db')
            assert conn_mock.execute.called

    @pytest.mark.asyncio
    async def test_run_migrations(self):
        with patch('alembic.command.upgrade') as mock_upgrade:
            await TenantProvisioner.run_migrations(
                'tenant_db', db_host='10.0.0.1', db_port=5433,
                db_user='t_user', db_password='t_pass',
            )
            mock_upgrade.assert_called_once()
            cfg = mock_upgrade.call_args[0][0]
            url = cfg.get_main_option('sqlalchemy.url')
            assert 'tenant_db' in url
            assert 't_user:t_pass' in url
            assert '10.0.0.1:5433' in url

    @pytest.mark.asyncio
    async def test_run_migrations_raises_on_failure(self):
        with patch('alembic.command.upgrade', side_effect=RuntimeError('mig failed')):
            with pytest.raises(TenantProvisionError) as exc:
                await TenantProvisioner.run_migrations('bad_db')
            assert 'Migration failed' in str(exc.value)

    @pytest.mark.asyncio
    async def test_provision_full_flow(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = None
        conn_mock.fetchval.return_value = 'new-tenant-id'

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
            patch('db.tenant_provisioner.TenantProvisioner.create_initial_admin',
                  new=AsyncMock(return_value='admin-password-123')),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            result = await TenantProvisioner.provision(
                slug='test-clinic', name='Test Clinic',
                domain='test.clinic.com',
            )

            assert isinstance(result, dict)
            assert result['tenant_id'] == 'new-tenant-id'
            assert result['admin_password'] == 'admin-password-123'

    @pytest.mark.asyncio
    async def test_provision_uses_slug_for_db_name(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = None
        conn_mock.fetchval.return_value = 'id-1'

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
            patch('db.tenant_provisioner.TenantProvisioner.create_initial_admin',
                  new=AsyncMock(return_value='pass')),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            await TenantProvisioner.provision(slug='my-clinic', name='My Clinic')
            sql = conn_mock.execute.call_args[0][0]
            assert 'my_clinic' in sql

    @pytest.mark.asyncio
    async def test_provision_raises_on_duplicate_slug(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = {'id': 'existing', 'slug': 'existing', 'db_name': 'existing'}

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            with pytest.raises(TenantProvisionError) as exc:
                await TenantProvisioner.provision(slug='existing', name='Existing')
            assert 'already exists' in str(exc.value)
