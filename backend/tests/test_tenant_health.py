from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tenant_health import TenantHealthHandler
from api.validate import _ValidationException, validation_exception_handler


def _http_exception(request, exc):
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    return Starlette(
        routes=[Route('/tenants/health', endpoint=TenantHealthHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _tenant(slug, name, **overrides):
    row = {
        'id': f'id-{slug}',
        'name': name,
        'slug': slug,
        'db_name': slug.replace('-', '_'),
        'db_host': '127.0.0.1',
        'db_port': 5432,
        'db_user': 'quantumpacs',
        'db_password': 'secret',
        'status': 'active',
        'storage_quota_bytes': 10_000_000,
        'storage_used_bytes': 2_500_000,
        'created_at': '2026-07-01',
        'updated_at': '2026-07-01',
    }
    row.update(overrides)
    return row


def _platform_conn(tenant_rows, info_rows):
    conn = AsyncMock()
    conn.fetch.return_value = tenant_rows
    conn.fetchrow.side_effect = info_rows
    return conn


def _pool_for(fetchval_side_effect):
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetchval.side_effect = fetchval_side_effect
    pool.acquire.return_value = conn
    return pool


def _tenant_health_user():
    return User({'id': 1, 'permissions': ['METERING_READ']})


class TestTenantHealth:
    def test_requires_metering_read(self):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.get('/tenants/health')
        assert resp.status_code == 403

    def test_returns_health_shape_for_each_tenant(self):
        rows = [_tenant('acme-clinic', 'Acme Clinic')]
        platform_conn = _platform_conn(rows, [dict(rows[0])])
        good_pool = _pool_for([1, '2026-07-25 10:30:00+00'])
        client = TestClient(_make_app(_tenant_health_user()))
        with (
            patch('api.tenant_health.get_conn') as mock_get_conn,
            patch('api.tenant_health.get_today_calls', new=AsyncMock(return_value=42)),
            patch('api.tenant_health.TenantConnectionPool.get',
                  new=AsyncMock(return_value=good_pool)),
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=platform_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            resp = client.get('/tenants/health')

        assert resp.status_code == 200
        tenants = resp.json()['tenants']
        assert len(tenants) == 1
        entry = tenants[0]
        assert entry['slug'] == 'acme-clinic'
        assert entry['name'] == 'Acme Clinic'
        assert entry['status'] == 'active'
        assert entry['db_reachable'] is True
        assert isinstance(entry['latency_ms'], (int, float))
        assert entry['last_activity'] == '2026-07-25 10:30:00+00'
        assert entry['storage_pct'] == 25.0
        assert entry['api_calls_today'] == 42
        assert entry['error'] is None

    def test_bogus_tenant_does_not_fail_whole_response(self):
        good = _tenant('acme-clinic', 'Acme Clinic')
        bogus = _tenant('bogus-clinic', 'Bogus Clinic')
        platform_conn = _platform_conn(
            [good, bogus],
            [dict(good), dict(bogus)],
        )
        good_pool = _pool_for([1, None])

        def _fake_get(slug, info=None):
            if slug == 'bogus-clinic':
                raise ConnectionError('connection refused')
            return good_pool

        client = TestClient(_make_app(_tenant_health_user()))
        with (
            patch('api.tenant_health.get_conn') as mock_get_conn,
            patch('api.tenant_health.get_today_calls', new=AsyncMock(return_value=0)),
            patch('api.tenant_health.TenantConnectionPool.get', side_effect=_fake_get),
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=platform_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            resp = client.get('/tenants/health')

        assert resp.status_code == 200
        tenants = {t['slug']: t for t in resp.json()['tenants']}
        assert tenants['acme-clinic']['db_reachable'] is True
        assert tenants['acme-clinic']['error'] is None
        assert tenants['bogus-clinic']['db_reachable'] is False
        assert tenants['bogus-clinic']['latency_ms'] is None
        assert 'connection refused' in tenants['bogus-clinic']['error']

    def test_decommissioned_tenants_are_skipped(self):
        platform_conn = _platform_conn([], [])
        client = TestClient(_make_app(_tenant_health_user()))
        with patch('api.tenant_health.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=platform_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            resp = client.get('/tenants/health')
        assert resp.status_code == 200
        assert resp.json()['tenants'] == []
