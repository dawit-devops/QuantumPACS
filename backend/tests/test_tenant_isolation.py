"""Cross-tenant isolation fuzz tests.
Property-based approach: for N tenant pairs with various configurations,
verify that each tenant's connection pool is isolated and middleware routing
is correct."""
import asyncio
import itertools
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from db.tenants import Tenants, TenantConnectionPool


# ── Helpers ──────────────────────────────────────────────────────────────

TENANT_FIXTURES = [
    {'slug': 'clinic-alfa', 'db_name': 'alfa_db', 'db_host': 'pg-1.local'},
    {'slug': 'clinic-bravo', 'db_name': 'bravo_db', 'db_host': 'pg-2.local'},
    {'slug': 'clinic-charlie', 'db_name': 'charlie_db', 'db_host': 'pg-3.local'},
    {'slug': 'clinic-delta', 'db_name': 'delta_db', 'db_host': 'pg-1.local'},
    {'slug': 'clinic-echo', 'db_name': 'echo_db', 'db_host': 'pg-2.local'},
]


def _make_middleware_app(user):
    from api.tenant_middleware import TenantMiddleware

    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Starlette(
        routes=[
            Route('/api/tenant-info', endpoint=_tenant_info),
            Route('/api/noop', endpoint=_noop),
        ],
        middleware=[
            Middleware(FakeAuth),
            Middleware(TenantMiddleware),
        ],
    )


async def _tenant_info(request):
    slug = getattr(request.state, 'tenant_slug', None)
    info = getattr(request.state, 'tenant', None)
    return JSONResponse({
        'slug': slug,
        'name': info.get('name') if info else None,
    })


async def _noop(request):
    return JSONResponse({'ok': True})


def _clean_pools():
    TenantConnectionPool._pools.clear()
    TenantConnectionPool._last_used.clear()


# ── 1. Pool Identity Isolation ───────────────────────────────────────────

class TestPoolIdentityIsolation:
    """Verify that distinct tenants always get distinct pool objects."""

    @pytest.mark.asyncio
    async def test_different_slugs_produce_different_pools(self):
        _clean_pools()
        slugs = [t['slug'] for t in TENANT_FIXTURES]
        infos = {t['slug']: t for t in TENANT_FIXTURES}

        pools = {}
        async def fake_create_pool(**kw):
            pool = AsyncMock()
            pool._db_name = kw.get('database')
            return pool

        with patch('asyncpg.create_pool', new=fake_create_pool):
            for slug in slugs:
                pools[slug] = await TenantConnectionPool.get(slug, infos[slug])

        pool_ids = {slug: id(p) for slug, p in pools.items()}
        assert len(set(pool_ids.values())) == len(slugs), \
            f'Expected {len(slugs)} unique pools, got {len(set(pool_ids.values()))}'

        for slug, pool in pools.items():
            assert pool._db_name == infos[slug]['db_name'], \
                f'Pool for {slug} has wrong db_name: {pool._db_name}'

    @pytest.mark.asyncio
    async def test_get_stats_queries_correct_database(self):
        _clean_pools()
        tenant_slug = 'clinic-alfa'
        info = {'db_name': 'alfa_db', 'db_host': 'pg-1.local'}

        conn_mock = AsyncMock()
        conn_mock.fetchval.side_effect = [10, 25, 100, 5000, None]
        ctx = MagicMock()
        ctx.__aenter__.return_value = conn_mock
        ctx.__aexit__.return_value = None

        pool_mock = AsyncMock()
        pool_mock.acquire = MagicMock(return_value=ctx)

        with patch('asyncpg.create_pool', new=AsyncMock(return_value=pool_mock)):
            result = await Tenants(conn=AsyncMock()).get_stats(tenant_slug, info)

        assert result['user_count'] == 10
        assert result['study_count'] == 25
        assert result['file_count'] == 100

    @pytest.mark.asyncio
    async def test_ten_random_tenant_pairs_are_isolated(self):
        _clean_pools()
        pairs = random.sample(list(itertools.combinations(TENANT_FIXTURES, 2)), min(10, 10))
        pairs_tested = 0

        for t1, t2 in pairs:
            _clean_pools()
            created = {}

            async def tracking_pool(**kw):
                pool = AsyncMock()
                pool._cfg = (kw.get('database'), kw.get('host'))
                return pool

            with patch('asyncpg.create_pool', new=tracking_pool):
                p1_name = t1['slug']
                p2_name = t2['slug']
                p1 = await TenantConnectionPool.get(p1_name, t1)
                created[p1_name] = p1._cfg
                p2 = await TenantConnectionPool.get(p2_name, t2)
                created[p2_name] = p2._cfg

                assert p1 is not p2, f'{p1_name} and {p2_name} share the same pool object'
                assert p1._cfg[0] != p2._cfg[0], \
                    f'Pools for {p1_name} and {p2_name} target the same database: {p1._cfg[0]}'
                pairs_tested += 1

        assert pairs_tested >= 5, f'Only tested {pairs_tested} pairs'


# ── 2. Middleware Routing Fuzz ────────────────────────────────────────────

class TestMiddlewareRoutingFuzz:
    """Combinatorial fuzz: for user claim × tenant header permutations,
    verify correct routing behavior."""

    ROUTING_CASES = [
        # (user_admin, user_tenant, header_tenant, expected_status)
        (True,  None,   'clinic-alfa',   200),  # admin, any header → ok
        (True,  None,   None,            200),  # admin, no header → ok
        (True,  None,   'unknown-slug',  404),  # admin, bad slug → 404
        (False, 'clinic-alfa', 'clinic-alfa',  200),  # own tenant → ok
        (False, 'clinic-alfa', 'clinic-bravo', 403),  # wrong tenant → 403
        (False, 'clinic-alfa', None,           403),  # claim, no registry row → fail closed (R5-04)
        (False, 'clinic-alfa', 'unknown-slug', 403),  # tenant mismatch → 403 before DB lookup
        (False, None,   'clinic-alfa',  403),  # no tenant claim → 403
        (False, None,   None,           200),  # no claim, no header → ok
    ]

    @pytest.mark.parametrize('is_admin,user_tenant,header_tenant,expected', ROUTING_CASES)
    def test_routing_combinations(self, is_admin, user_tenant, header_tenant, expected):
        user = User({'id': 1, 'admin': is_admin})
        if user_tenant is not None:
            user.tenant = user_tenant

        mock_info = None
        if header_tenant in ('clinic-alfa', 'clinic-bravo'):
            mock_info = {'slug': header_tenant, 'name': header_tenant.title(),
                         'db_name': header_tenant.replace('-', '_')}

        mock_pool = AsyncMock()
        client = TestClient(_make_middleware_app(user))

        headers = {}
        if header_tenant:
            headers['X-Tenant-ID'] = header_tenant

        with (patch('api.tenant_middleware.get_conn') as mock_get_conn,
              patch('api.tenant_middleware.TenantConnectionPool.get',
                    new=AsyncMock(return_value=mock_pool))):
            if mock_info is None:
                mock_ctx = AsyncMock()
                conn_mock = AsyncMock()
                conn_mock.fetchrow.return_value = mock_info
                mock_ctx.__aenter__.return_value = conn_mock
                mock_get_conn.return_value = mock_ctx
            else:
                mock_ctx = AsyncMock()
                conn_mock = AsyncMock()
                conn_mock.fetchrow.return_value = mock_info
                mock_ctx.__aenter__.return_value = conn_mock
                mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/noop', headers=headers)

        assert resp.status_code == expected, \
            f'admin={is_admin} user_tenant={user_tenant} header={header_tenant}: ' \
            f'expected {expected}, got {resp.status_code}'

    def test_random_tenant_header_no_bleed(self):
        """Sending tenant header X should not expose data from unrelated tenant Y."""
        user = User({'id': 1, 'admin': True})

        for _ in range(20):
            slug = random.choice(TENANT_FIXTURES)['slug']
            mock_info = {'slug': slug, 'name': slug.title(), 'db_name': slug.replace('-', '_')}
            mock_pool = AsyncMock()

            client = TestClient(_make_middleware_app(user))
            with (patch('api.tenant_middleware.get_conn') as mock_get_conn,
                  patch('api.tenant_middleware.TenantConnectionPool.get',
                        new=AsyncMock(return_value=mock_pool))):
                mock_ctx = AsyncMock()
                conn_mock = AsyncMock()
                conn_mock.fetchrow.return_value = mock_info
                mock_ctx.__aenter__.return_value = conn_mock
                mock_get_conn.return_value = mock_ctx

                resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': slug})
                assert resp.status_code == 200
                assert resp.json()['slug'] == slug, \
                    f'Request for {slug} returned slug={resp.json()["slug"]}'


# ── 3. Connection Pool LRU Eviction ──────────────────────────────────────

class TestLruEvictionIsolation:
    """Verify LRU eviction doesn't close the wrong tenant's pool."""

    @pytest.mark.asyncio
    async def test_evict_removes_only_oldest(self):
        _clean_pools()
        pool_mock = AsyncMock()

        for i, t in enumerate(TENANT_FIXTURES[:4]):
            TenantConnectionPool._pools[t['slug']] = pool_mock
            TenantConnectionPool._last_used[t['slug']] = float(i)

        oldest_slug = min(TenantConnectionPool._last_used, key=TenantConnectionPool._last_used.get)

        TenantConnectionPool._evict_lru()
        await asyncio.sleep(0)

        assert oldest_slug not in TenantConnectionPool._pools

    @pytest.mark.asyncio
    async def test_evict_keeps_other_pools_intact(self):
        _clean_pools()
        pool = AsyncMock()
        async def mkpool(**kw): return pool

        with patch('asyncpg.create_pool', new=mkpool):
            for t in TENANT_FIXTURES[:3]:
                await TenantConnectionPool.get(t['slug'], t)

        slugs_before = set(TenantConnectionPool._pools.keys())
        TenantConnectionPool._evict_lru()
        await asyncio.sleep(0)
        slugs_after = set(TenantConnectionPool._pools.keys())

        removed = slugs_before - slugs_after
        assert len(removed) == 1, f'Expected exactly 1 eviction, got {removed}'

    @pytest.mark.asyncio
    async def test_refresh_resets_lru_order(self):
        _clean_pools()
        pool = AsyncMock()
        async def mkpool(**kw): return pool

        with patch('asyncpg.create_pool', new=mkpool):
            await TenantConnectionPool.get('clinic-alfa', TENANT_FIXTURES[0])
            await TenantConnectionPool.get('clinic-bravo', TENANT_FIXTURES[1])

            TenantConnectionPool._last_used['clinic-alfa'] = 0.0
            TenantConnectionPool._last_used['clinic-bravo'] = 1.0

            await TenantConnectionPool.get('clinic-alfa')

            assert TenantConnectionPool._last_used['clinic-alfa'] > \
                   TenantConnectionPool._last_used['clinic-bravo'], \
                'Re-getting alfa should make it newer than bravo'


# ── 4. Concurrent Access Isolation ───────────────────────────────────────

class TestConcurrentIsolation:
    """Verify that concurrent requests to different tenants use separate pools."""

    @pytest.mark.asyncio
    async def test_concurrent_gets_use_correct_pools(self):
        _clean_pools()
        call_log = []

        async def logging_pool(**kw):
            call_log.append(kw.get('database'))
            return AsyncMock()

        with patch('asyncpg.create_pool', new=logging_pool):
            results = await asyncio.gather(
                TenantConnectionPool.get('clinic-alfa', TENANT_FIXTURES[0]),
                TenantConnectionPool.get('clinic-bravo', TENANT_FIXTURES[1]),
                TenantConnectionPool.get('clinic-charlie', TENANT_FIXTURES[2]),
            )

        assert len(results) == 3
        assert all(r is not None for r in results)
        assert results[0] is not results[1]
        assert set(call_log) == {'alfa_db', 'bravo_db', 'charlie_db'}, \
            f'Called create_pool with databases: {call_log}'

    @pytest.mark.asyncio
    async def test_concurrent_stats_no_crosstalk(self):
        _clean_pools()
        info_alfa = {'db_name': 'alfa_db', 'db_host': 'pg-1.local'}
        info_bravo = {'db_name': 'bravo_db', 'db_host': 'pg-2.local'}

        conn_alfa = AsyncMock()
        conn_alfa.fetchval.side_effect = [5, 10, 20, 1000, None]
        conn_bravo = AsyncMock()
        conn_bravo.fetchval.side_effect = [3, 7, 15, 500, None]

        ctx_alfa = MagicMock()
        ctx_alfa.__aenter__.return_value = conn_alfa
        ctx_alfa.__aexit__.return_value = None
        ctx_bravo = MagicMock()
        ctx_bravo.__aenter__.return_value = conn_bravo
        ctx_bravo.__aexit__.return_value = None

        pool_alfa = AsyncMock()
        pool_alfa.acquire = MagicMock(return_value=ctx_alfa)
        pool_bravo = AsyncMock()
        pool_bravo.acquire = MagicMock(return_value=ctx_bravo)

        call_count = 0
        async def routing_pool(**kw):
            nonlocal call_count
            call_count += 1
            if kw.get('database') == 'alfa_db':
                return pool_alfa
            if kw.get('database') == 'bravo_db':
                return pool_bravo
            return AsyncMock()

        with patch('asyncpg.create_pool', new=routing_pool):
            stats_a, stats_b = await asyncio.gather(
                Tenants(conn=AsyncMock()).get_stats('clinic-alfa', info_alfa),
                Tenants(conn=AsyncMock()).get_stats('clinic-bravo', info_bravo),
            )

        assert stats_a['user_count'] == 5
        assert stats_a['study_count'] == 10
        assert stats_b['user_count'] == 3
        assert stats_b['study_count'] == 7
        assert call_count == 2


# ── 5. Edge Cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases and malformed inputs."""

    @pytest.mark.asyncio
    async def test_empty_slug_creates_new_pool(self):
        _clean_pools()
        pool = AsyncMock()
        async def mkpool(**kw): return pool

        with patch('asyncpg.create_pool', new=mkpool):
            result = await TenantConnectionPool.get('', {'db_name': 'empty_db'})
            assert result is pool
            assert '' in TenantConnectionPool._pools

    @pytest.mark.asyncio
    async def test_unknown_tenant_raises_keyerror(self):
        _clean_pools()
        with pytest.raises(KeyError):
            await TenantConnectionPool.get('nonexistent')

    @pytest.mark.asyncio
    async def test_missing_db_name_in_info_raises_keyerror(self):
        _clean_pools()
        with pytest.raises(KeyError):
            await TenantConnectionPool.get('broken', {'db_host': 'localhost'})
