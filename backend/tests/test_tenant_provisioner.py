from unittest.mock import AsyncMock, patch

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
            ddl = [c[0][0] for c in conn_mock.execute.call_args_list
                   if 'CREATE DATABASE' in c[0][0]]
            assert ddl and 'my_clinic' in ddl[0]

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

    @pytest.mark.asyncio
    async def test_provision_rejects_second_main_db_tenant(self):
        # F-2: a tenant whose data store resolves to the main database must be
        # refused unless it is the designated `default` tenant.
        fake_config = {
            'db_database': 'maindb', 'db_host': 'h',
            'db_user': 'u', 'db_password': 'p', 'db_port': '5432',
        }
        with (
            patch('db.tenant_provisioner.config', fake_config),
            patch('db.tenants.config', fake_config),
        ):
            with pytest.raises(TenantProvisionError) as exc:
                await TenantProvisioner.provision(
                    slug='rogue', name='Rogue',
                    db_name='maindb',  # same name as the main database
                )
            assert 'main database' in str(exc.value)

    @pytest.mark.asyncio
    async def test_provision_allows_default_tenant_on_main_db(self):
        # The seeded `default` tenant is the only tenant permitted to share the
        # main database; the F-2 guard must not fire for it.
        fake_config = {
            'db_database': 'maindb', 'db_host': 'h',
            'db_user': 'u', 'db_password': 'p', 'db_port': '5432',
        }
        conn_mock = AsyncMock()
        with (
            patch('db.tenant_provisioner.config', fake_config),
            patch('db.tenants.config', fake_config),
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
            patch('db.tenant_provisioner.TenantProvisioner.create_initial_admin',
                  new=AsyncMock(return_value='pass')),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx
            conn_mock.fetchrow.return_value = None  # no existing slug
            # Should pass the guard and proceed (DuplicateDatabaseError on the
            # main db is expected and handled, so it returns a result/raises a
            # provision error from later steps — but NOT the main-db guard).
            try:
                await TenantProvisioner.provision(
                    slug='default', name='Default', db_name='maindb',
                )
            except TenantProvisionError as e:
                assert 'main database' not in str(e)


class TestProvisionerRisDefaults:
    """D6: a freshly provisioned tenant must come with default RIS
    capacity (resources) and report templates, so the scheduling and
    reading consoles are usable without manual setup. Seeding runs after
    migrations but before the registry flips to active."""

    def _provision_ctx(self, conn_mock):
        mock_get_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = conn_mock
        mock_get_conn.return_value = mock_ctx
        return mock_get_conn

    @pytest.mark.asyncio
    async def test_provision_seeds_ris_defaults(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = None
        conn_mock.fetchval.return_value = 'new-tenant-id'

        seeded = []

        async def fake_seed(db_name, slug, **kw):
            seeded.append((db_name, slug))

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade'),
            patch('db.tenant_provisioner.TenantProvisioner.create_initial_admin',
                  new=AsyncMock(return_value='pass')),
            patch('db.tenant_provisioner.TenantProvisioner.seed_ris_defaults',
                  new=fake_seed),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            await TenantProvisioner.provision(
                slug='clinic-d6', name='Clinic D6',
                db_name='clinic_d6',
            )
            assert seeded, 'provision must seed RIS defaults after migrations'
            db_name, slug = seeded[0]
            assert db_name == 'clinic_d6'
            assert slug == 'clinic-d6'

    @pytest.mark.asyncio
    async def test_seed_ris_defaults_is_idempotent(self):
        """Re-running the seeder against an already-seeded DB must not
        duplicate rows (UNIQUE (tenant_id, name) on resources; the
        templates insert guards on name+tenant)."""
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        with patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)):
            await TenantProvisioner.seed_ris_defaults('clinic_d6', 'clinic-d6')
            sqls = [c[0][0] for c in conn_mock.execute.call_args_list]
            # resources use ON CONFLICT DO NOTHING (idempotent by name)
            assert any('ON CONFLICT' in s and 'ris_resources' in s for s in sqls), \
                'resource seeding must be idempotent (ON CONFLICT DO NOTHING)'
            assert any('ris_report_templates' in s for s in sqls), \
                'template seeding must insert default report templates'
            assert any('NOT EXISTS' in s and 'ris_report_templates' in s for s in sqls), \
                'template seeding must be idempotent (NOT EXISTS name guard)'


class TestProvisionerRollbackCleanup:
    """D6: a failed provision marks the registry decommissioned AND drops
    the half-created tenant database, so retries do not collide on a
    half-migrated DB."""

    @pytest.mark.asyncio
    async def test_failed_provision_drops_database(self):
        conn_mock = AsyncMock()
        conn_mock.fetchrow.return_value = None
        conn_mock.fetchval.return_value = 'new-tenant-id'

        with (
            patch('asyncpg.connect', new=AsyncMock(return_value=conn_mock)),
            patch('db.tenant_provisioner.get_conn') as mock_get_conn,
            patch('alembic.command.upgrade',
                  side_effect=RuntimeError('mig failed')),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            with pytest.raises(TenantProvisionError):
                await TenantProvisioner.provision(
                    slug='bad-db', name='Bad DB', db_name='bad_db',
                )
            # status flipped to decommissioned (set_status uses fetchval)
            status_vals = [c.args[0] for c in conn_mock.fetchval.call_args_list]
            assert any('decommissioned' in (s or '') for s in status_vals), \
                'failed provision must decommission the registry row'
            # half-created database dropped
            drop_calls = [
                c for c in conn_mock.execute.call_args_list
                if 'DROP DATABASE' in c[0][0] and 'bad_db' in c[0][0]
            ]
            assert drop_calls, 'failed provision must DROP the half-created database'
