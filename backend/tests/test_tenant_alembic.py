import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTenantUrlResolution:
    @pytest.mark.asyncio
    async def test_get_tenant_url_returns_none_without_slug(self):
        from migrations.tenant_url import async_get_tenant_url
        result = await async_get_tenant_url()
        assert result is None

        result = await async_get_tenant_url(slug=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_url_resolves_from_registry(self):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'db_name': 'my_clinic_db',
            'db_host': '10.0.0.5',
            'db_port': 5432,
            'db_user': 'tenant_user',
            'db_password': 'tenant_pass',
        }

        with patch('asyncpg.connect', new=AsyncMock(return_value=mock_conn)):
            from migrations.tenant_url import async_get_tenant_url
            url = await async_get_tenant_url(slug='my-clinic')

            assert 'my_clinic_db' in url
            assert 'tenant_user:tenant_pass' in url
            assert '10.0.0.5' in url

    @pytest.mark.asyncio
    async def test_get_tenant_url_raises_on_missing(self):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch('asyncpg.connect', new=AsyncMock(return_value=mock_conn)):
            from migrations.tenant_url import async_get_tenant_url
            with pytest.raises(RuntimeError, match='not found'):
                await async_get_tenant_url(slug='nonexistent')

    @pytest.mark.asyncio
    async def test_get_tenant_url_uses_env_slug(self):
        os.environ['TENANT_SLUG'] = 'env-clinic'
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            'db_name': 'env_clinic_db', 'db_host': 'localhost',
            'db_port': 5432, 'db_user': 'u', 'db_password': 'p',
        }

        with patch('asyncpg.connect', new=AsyncMock(return_value=mock_conn)):
            import importlib
            import migrations.tenant_url
            importlib.reload(migrations.tenant_url)

            url = await migrations.tenant_url.async_get_tenant_url()
            assert 'env_clinic_db' in url

        os.environ.pop('TENANT_SLUG', None)
        importlib.reload(migrations.tenant_url)


class TestTenantMigrateCommand:
    @pytest.mark.asyncio
    async def test_migrate_all_tenants(self):
        mock_tenants = [
            {'slug': 'clinic-a', 'db_name': 'clinic_a', 'db_host': 'localhost',
             'db_port': 5432, 'db_user': 'u', 'db_password': 'p'},
            {'slug': 'clinic-b', 'db_name': 'clinic_b', 'db_host': 'localhost',
             'db_port': 5432, 'db_user': 'u', 'db_password': 'p'},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_tenants
        mock_ctx = MagicMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_ctx)
        mock_pool.close = AsyncMock()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'', None))

        import management.tenant_migrate as tenant_migrate

        with (
            patch('asyncpg.create_pool', new=AsyncMock(return_value=mock_pool)),
            patch('asyncio.create_subprocess_exec',
                  new=AsyncMock(return_value=mock_proc)),
        ):
            with patch.object(sys, 'argv', ['tenant_migrate.py']):
                await tenant_migrate.main()

        assert mock_proc.communicate.call_count == 2

    @pytest.mark.asyncio
    async def test_migrate_specific_tenant(self):
        mock_tenants = [
            {'slug': 'clinic-a', 'db_name': 'clinic_a', 'db_host': 'localhost',
             'db_port': 5432, 'db_user': 'u', 'db_password': 'p'},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_tenants
        mock_ctx = MagicMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_ctx)
        mock_pool.close = AsyncMock()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'', None))

        import management.tenant_migrate as tenant_migrate

        with (
            patch('asyncpg.create_pool', new=AsyncMock(return_value=mock_pool)),
            patch('asyncio.create_subprocess_exec',
                  new=AsyncMock(return_value=mock_proc)),
        ):
            with patch.object(sys, 'argv', ['tenant_migrate.py', 'clinic-a']):
                await tenant_migrate.main()

        assert mock_proc.communicate.call_count == 1

    @pytest.mark.asyncio
    async def test_migrate_sets_tenant_slug_env(self):
        mock_tenants = [{'slug': 'my-clinic', 'db_name': 'my_clinic', 'db_host': 'localhost',
                         'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}]

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_tenants
        mock_ctx = MagicMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_ctx)
        mock_pool.close = AsyncMock()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'', None))

        import management.tenant_migrate as tenant_migrate

        with (
            patch('asyncpg.create_pool', new=AsyncMock(return_value=mock_pool)),
            patch('asyncio.create_subprocess_exec',
                  new=AsyncMock(return_value=mock_proc)) as mock_exec,
        ):
            with patch.object(sys, 'argv', ['tenant_migrate.py']):
                await tenant_migrate.main()

        env = mock_exec.call_args[1]['env']
        assert env.get('TENANT_SLUG') == 'my-clinic'
