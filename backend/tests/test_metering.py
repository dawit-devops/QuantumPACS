from unittest.mock import AsyncMock, patch

import pytest

from db.metering import get_platform_usage, get_usage, record_request, record_storage


def _conn_ctx(conn):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


class TestRecordRequest:
    @pytest.mark.asyncio
    async def test_upsert_increments_api_calls(self):
        conn = AsyncMock()
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            await record_request('acme-clinic')
        sql, slug = conn.execute.call_args[0]
        assert 'tenant_usage_daily' in sql
        assert 'ON CONFLICT (slug, day) DO UPDATE' in sql
        assert 'api_calls = tenant_usage_daily.api_calls + 1' in sql
        assert slug == 'acme-clinic'

    @pytest.mark.asyncio
    async def test_upsert_increments_on_second_call(self):
        conn = AsyncMock()
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            await record_request('acme-clinic')
            await record_request('acme-clinic')
        assert conn.execute.call_count == 2
        for call in conn.execute.call_args_list:
            assert 'api_calls = tenant_usage_daily.api_calls + 1' in call.args[0]

    @pytest.mark.asyncio
    async def test_never_raises_on_db_failure(self):
        with patch('db.metering.get_conn', side_effect=RuntimeError('db down')):
            await record_request('acme-clinic')


class TestGetUsage:
    @pytest.mark.asyncio
    async def test_returns_rows_for_last_days(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'slug': 'acme-clinic', 'day': '2026-08-05', 'api_calls': 3,
             'storage_bytes': 100, 'active_users': 2},
            {'slug': 'acme-clinic', 'day': '2026-08-06', 'api_calls': 5,
             'storage_bytes': 120, 'active_users': 3},
        ]
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            rows = await get_usage('acme-clinic', days=7)
        assert len(rows) == 2
        assert rows[0]['api_calls'] == 3
        assert rows[1]['active_users'] == 3
        sql, slug, days = conn.fetch.call_args[0]
        assert 'tenant_usage_daily' in sql
        assert 'ORDER BY day' in sql
        assert slug == 'acme-clinic'
        assert days == 7


class TestGetPlatformUsage:
    @pytest.mark.asyncio
    async def test_returns_per_tenant_totals(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'slug': 'acme-clinic', 'name': 'Acme Clinic', 'api_calls': 50,
             'storage_bytes': 5000, 'active_users': 4},
            {'slug': 'beta-rad', 'name': 'Beta Radiology', 'api_calls': 20,
             'storage_bytes': 2000, 'active_users': 2},
        ]
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            rows = await get_platform_usage(days=30)
        assert len(rows) == 2
        assert rows[0]['api_calls'] == 50
        assert rows[0]['storage_bytes'] == 5000
        sql = conn.fetch.call_args[0][0]
        assert 'FROM tenant_usage_daily u' in sql
        assert 'LEFT JOIN tenants t' in sql
        assert 'ORDER BY api_calls DESC' in sql


class TestRecordStorage:
    @pytest.mark.asyncio
    async def test_sets_todays_storage_bytes(self):
        conn = AsyncMock()
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            await record_storage('acme-clinic', 12345)
        sql, slug, size = conn.execute.call_args[0]
        assert 'tenant_usage_daily' in sql
        assert 'storage_bytes = EXCLUDED.storage_bytes' in sql
        assert slug == 'acme-clinic'
        assert size == 12345
