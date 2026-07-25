from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.tenants import Tenants


class TestTenantStats:
    def _mock_pool(self, fetchval_side_effect):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = fetchval_side_effect
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_ctx
        return mock_pool, mock_conn

    @pytest.mark.asyncio
    async def test_get_stats_returns_all_fields(self):
        mock_pool, mock_conn = self._mock_pool([10, 25, 100, 5000000, None])

        t = Tenants(conn=None)

        with patch('db.tenants.TenantConnectionPool.get', new=AsyncMock(return_value=mock_pool)):
            stats = await t.get_stats('test-clinic', {'db_name': 'test_clinic'})

        assert stats['user_count'] == 10
        assert stats['study_count'] == 25
        assert stats['file_count'] == 100
        assert stats['storage_used_bytes'] == 5000000
        assert stats['last_activity'] is None

    @pytest.mark.asyncio
    async def test_get_stats_with_last_activity(self):
        mock_pool, mock_conn = self._mock_pool([5, 10, 50, 1000000, '2026-07-25 10:30:00+00'])

        t = Tenants(conn=None)

        with patch('db.tenants.TenantConnectionPool.get', new=AsyncMock(return_value=mock_pool)):
            stats = await t.get_stats('active-clinic', {'db_name': 'active_clinic'})

        assert stats['user_count'] == 5
        assert stats['study_count'] == 10
        assert stats['file_count'] == 50
        assert stats['storage_used_bytes'] == 1000000
        assert stats['last_activity'] == '2026-07-25 10:30:00+00'

    @pytest.mark.asyncio
    async def test_get_stats_handles_empty_database(self):
        mock_pool, mock_conn = self._mock_pool([0, 0, 0, None, None])

        t = Tenants(conn=None)

        with patch('db.tenants.TenantConnectionPool.get', new=AsyncMock(return_value=mock_pool)):
            stats = await t.get_stats('empty', {'db_name': 'empty'})

        assert stats['user_count'] == 0
        assert stats['study_count'] == 0
        assert stats['file_count'] == 0
        assert stats['storage_used_bytes'] == 0
        assert stats['last_activity'] is None

    @pytest.mark.asyncio
    async def test_get_stats_coalesces_null_storage(self):
        mock_pool, mock_conn = self._mock_pool([3, 7, 15, None, None])

        t = Tenants(conn=None)

        with patch('db.tenants.TenantConnectionPool.get', new=AsyncMock(return_value=mock_pool)):
            stats = await t.get_stats('some', {'db_name': 'some'})

        assert stats['storage_used_bytes'] == 0
