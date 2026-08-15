from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tenants import TenantsHandler
from api.validate import validation_exception_handler, _ValidationException
from db.tenants import Tenants


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({
            'id': 1, 'admin': True, 'permissions': ['TENANT_READ'], 'role': 'super_admin',
        })

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(user=None):
    return Starlette(
        routes=[Route('/tenants', endpoint=TenantsHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


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

        t = Tenants(conn=MagicMock())

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

        t = Tenants(conn=MagicMock())

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

        t = Tenants(conn=MagicMock())

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

        t = Tenants(conn=MagicMock())

        with patch('db.tenants.TenantConnectionPool.get', new=AsyncMock(return_value=mock_pool)):
            stats = await t.get_stats('some', {'db_name': 'some'})

        assert stats['storage_used_bytes'] == 0

    def test_list_enriches_tenant_with_counts(self):
        """P2-1 (tenant_admin review): the tenants list must carry real
        user_count/study_count/last_activity so cards never render "?" —
        stats are merged per visible tenant and stay scoped."""
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        registry = {
            'id': 't1', 'name': 'Default', 'slug': 'default', 'status': 'active',
            'storage_quota_bytes': 0, 'storage_used_bytes': 100,
        }

        async def fake_get_all(*a, **k):
            return [registry]

        stats = {
            'user_count': 23, 'study_count': 17, 'file_count': 20,
            'storage_used_bytes': 100, 'storage_quota_bytes': 0,
            'storage_pct': 0, 'last_activity': '2026-08-01 10:00:00+00',
        }
        mock_tenants = MagicMock()
        mock_tenants.get_all = AsyncMock(side_effect=fake_get_all)
        mock_stats = MagicMock()
        mock_stats.get_stats = AsyncMock(return_value=stats)

        def tenants_factory(conn=None):
            # List path constructs Tenants(get_conn()) for get_all and
            # Tenants(None) for get_stats — return per-conn instances.
            return mock_stats if conn is None else mock_tenants

        with (
            patch('api.tenants.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.tenants.Tenants', side_effect=tenants_factory),
        ):
            client = TestClient(_make_app())
            resp = client.get('/tenants')
        assert resp.status_code == 200
        row = resp.json()['data'][0]
        assert row['user_count'] == 23
        assert row['study_count'] == 17
        assert row['last_activity'] == '2026-08-01 10:00:00+00'
        # Registry row fields survive the merge.
        assert row['slug'] == 'default'
        assert row['storage_used_bytes'] == 100
