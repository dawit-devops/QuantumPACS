from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User


def _make_app(user):
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


class TestTenantMiddleware:
    def test_skips_when_no_tenant_header(self):
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_app(user))
        resp = client.get('/api/noop')
        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    def test_attaches_tenant_when_header_present(self):
        user = User({'id': 1, 'admin': True})
        mock_info = {'slug': 'test-clinic', 'name': 'Test Clinic', 'db_name': 'test_clinic'}
        mock_pool = AsyncMock()
        client = TestClient(_make_app(user))

        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn_mock = AsyncMock()
            conn_mock.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'test-clinic'})
            assert resp.status_code == 200
            data = resp.json()
            assert data['slug'] == 'test-clinic'
            assert data['name'] == 'Test Clinic'

    def test_returns_404_for_unknown_tenant(self):
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_app(user))

        with patch('api.tenant_middleware.get_conn') as mock_get_conn:
            mock_ctx = AsyncMock()
            conn_mock = AsyncMock()
            conn_mock.fetchrow.return_value = None
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'unknown'})
            assert resp.status_code == 404

    def test_denies_access_to_wrong_tenant(self):
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_app(user))

        resp = client.get('/api/noop', headers={'X-Tenant-ID': 'other-clinic'})
        assert resp.status_code == 403
        data = resp.json()
        assert 'tenant' in data.get('message', '').lower()

    def test_allows_access_to_own_tenant(self):
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        mock_info = {'slug': 'my-clinic', 'name': 'My Clinic', 'db_name': 'my_clinic'}
        mock_pool = AsyncMock()
        client = TestClient(_make_app(user))

        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn_mock = AsyncMock()
            conn_mock.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'my-clinic'})
            assert resp.status_code == 200
            assert resp.json()['slug'] == 'my-clinic'

    def test_admin_can_access_any_tenant(self):
        user = User({'id': 1, 'admin': True})
        mock_info = {'slug': 'hospital-x', 'name': 'Hospital X', 'db_name': 'hospital_x'}
        mock_pool = AsyncMock()
        client = TestClient(_make_app(user))

        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn_mock = AsyncMock()
            conn_mock.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'hospital-x'})
            assert resp.status_code == 200

    def test_tenantless_user_denied_any_tenant(self):
        user = User({'id': 3, 'admin': False})
        client = TestClient(_make_app(user))

        resp = client.get('/api/noop', headers={'X-Tenant-ID': 'any-clinic'})
        assert resp.status_code == 403

    def test_claim_without_registry_row_is_rejected(self):
        """R5-04: a JWT tenant with no registry row must not silently fall
        back to the main DB (the default tenant's data plane) — fail closed
        with 403."""
        user = User({'id': 1, 'admin': True, 'tenant': 'ghost-tenant'})
        client = TestClient(_make_app(user))

        with patch('api.tenant_middleware.get_conn') as mock_get_conn:
            mock_ctx = AsyncMock()
            conn_mock = AsyncMock()
            conn_mock.fetchrow.return_value = None
            mock_ctx.__aenter__.return_value = conn_mock
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/noop')
            assert resp.status_code == 403

    def test_effective_tenant_prefers_middleware_slug(self):
        """R5-05: under an X-Tenant-ID override the effective tenant is the
        middleware-resolved slug, not the JWT home tenant."""
        from api.tenant_middleware import effective_tenant

        user = User({'id': 2, 'admin': True, 'tenant': 'home-clinic'})
        request = _FakeRequest(user, tenant_slug='target-clinic')
        assert effective_tenant(request) == 'target-clinic'

        request = _FakeRequest(user, tenant_slug=None)
        assert effective_tenant(request) == 'home-clinic'


class _FakeRequest:
    def __init__(self, user, tenant_slug):
        self.user = user
        self.state = type('State', (), {'tenant_slug': tenant_slug})()
