from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import create_token, create_token_pair, verify_token
from db.tenants import TenantConnectionPool

SECRET = 'test-secret-key-for-tenancy-gate-tests!!'


def _make_app(user):
    from api.tenant_middleware import TenantMiddleware

    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Starlette(
        routes=[
            Route('/api/noop', endpoint=_noop),
            Route('/api/tenant-info', endpoint=_tenant_info),
        ],
        middleware=[
            Middleware(FakeAuth),
            Middleware(TenantMiddleware),
        ],
    )


async def _noop(request):
    return JSONResponse({'ok': True})


async def _tenant_info(request):
    slug = getattr(request.state, 'tenant_slug', None)
    info = getattr(request.state, 'tenant', None)
    return JSONResponse({
        'slug': slug,
        'name': info.get('name') if info else None,
    })


class TestTenantMiddlewareGating:
    def test_no_tenant_header_ok_for_admin(self):
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_app(user))
        resp = client.get('/api/noop')
        assert resp.status_code == 200

    def test_matching_tenant_allowed(self):
        mock_info = {'slug': 'my-clinic', 'name': 'My Clinic', 'db_name': 'my_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_app(user))

        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'my-clinic'})
            assert resp.status_code == 200
            assert resp.json()['slug'] == 'my-clinic'

    def test_mismatched_tenant_denied(self):
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_app(user))
        resp = client.get('/api/noop', headers={'X-Tenant-ID': 'other-clinic'})
        assert resp.status_code == 403

    def test_admin_can_access_any_tenant(self):
        mock_info = {'slug': 'hospital-x', 'name': 'Hospital X', 'db_name': 'hospital_x'}
        mock_pool = AsyncMock()
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_app(user))

        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'hospital-x'})
            assert resp.status_code == 200

    def test_tenantless_user_denied_any_tenant(self):
        user = User({'id': 3, 'admin': False})
        client = TestClient(_make_app(user))
        resp = client.get('/api/noop', headers={'X-Tenant-ID': 'any-clinic'})
        assert resp.status_code == 403

    def test_unknown_tenant_returns_404(self):
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_app(user))

        with patch('api.tenant_middleware.get_conn') as mock_get_conn:
            mock_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = None
            mock_ctx.__aenter__.return_value = conn
            mock_get_conn.return_value = mock_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'unknown'})
            assert resp.status_code == 404

    # ---- R2-03 cross-tenant clinical grants (teleradiology) ----

    def _stub_grant(self, mock_auth_conn, grant_exists=True):
        """Patch api.auth.get_conn so User.has_grant resolves the mock; the
        auth module holds its own get_conn reference (grant table lives in
        the main DB, read before the middleware scopes anything)."""
        auth_ctx = AsyncMock()
        auth_conn = AsyncMock()
        auth_conn.fetchval.return_value = 1 if grant_exists else None
        auth_ctx.__aenter__.return_value = auth_conn
        mock_auth_conn.return_value = auth_ctx

    def test_grant_holder_can_override_to_granted_tenant(self):
        mock_info = {'slug': 'other-clinic', 'name': 'Other Clinic', 'db_name': 'other_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        client = TestClient(_make_app(user))

        with (
            patch('api.auth.get_conn') as mock_auth_conn,
            patch('api.tenant_middleware.get_conn') as mock_mw_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            self._stub_grant(mock_auth_conn, grant_exists=True)
            mw_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mw_ctx.__aenter__.return_value = conn
            mock_mw_conn.return_value = mw_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'other-clinic'})
            assert resp.status_code == 200
            assert resp.json()['slug'] == 'other-clinic'

    def test_grant_row_without_permission_is_denied(self):
        # Defense in depth: the CROSS_TENANT_READ permission gate runs before
        # any DB lookup, so a stray grant row must stay inert.
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['STUDY_READ']})
        client = TestClient(_make_app(user))
        with patch.object(User, 'has_grant') as mock_has_grant:
            resp = client.get('/api/noop', headers={'X-Tenant-ID': 'other-clinic'})
            assert resp.status_code == 403
            mock_has_grant.assert_not_called()

    def test_permission_without_grant_row_is_denied(self):
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        client = TestClient(_make_app(user))

        with patch('api.auth.get_conn') as mock_auth_conn:
            self._stub_grant(mock_auth_conn, grant_exists=False)
            resp = client.get('/api/noop', headers={'X-Tenant-ID': 'other-clinic'})
            assert resp.status_code == 403

    def test_cross_tenant_access_is_audited(self):
        mock_info = {'slug': 'other-clinic', 'name': 'Other Clinic', 'db_name': 'other_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        client = TestClient(_make_app(user))

        with (
            patch('api.auth.get_conn') as mock_auth_conn,
            patch('api.tenant_middleware.get_conn') as mock_mw_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            self._stub_grant(mock_auth_conn, grant_exists=True)
            mw_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mw_ctx.__aenter__.return_value = conn
            mock_mw_conn.return_value = mw_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'other-clinic'})
            assert resp.status_code == 200

            audit_calls = [
                c for c in conn.execute.call_args_list
                if 'INSERT INTO logs' in c.args[0]
            ]
            assert len(audit_calls) == 1
            assert 'tenant.cross_tenant_access' in audit_calls[0].args[1]
            assert audit_calls[0].args[2] == 'other-clinic'
            assert '"actor": "7"' in audit_calls[0].args[1]

    def test_home_tenant_override_is_not_audited(self):
        # Same-tenant header (fast path, no grant) must not produce a
        # cross-tenant audit row.
        mock_info = {'slug': 'my-clinic', 'name': 'My Clinic', 'db_name': 'my_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_app(user))

        with (
            patch('api.auth.get_conn') as mock_auth_conn,
            patch('api.tenant_middleware.get_conn') as mock_mw_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            self._stub_grant(mock_auth_conn, grant_exists=False)
            mw_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mw_ctx.__aenter__.return_value = conn
            mock_mw_conn.return_value = mw_ctx

            resp = client.get('/api/tenant-info', headers={'X-Tenant-ID': 'my-clinic'})
            assert resp.status_code == 200
            audit_calls = [
                c for c in conn.execute.call_args_list
                if 'INSERT INTO logs' in c.args[0]
            ]
            assert audit_calls == []


class TestTenantPool:
    def setup_method(self):
        TenantConnectionPool._pools.clear()
        TenantConnectionPool._last_used.clear()

    @pytest.mark.asyncio
    async def test_get_returns_same_pool_for_same_tenant(self):
        info_a = {'db_name': 'tenant_a', 'db_host': 'localhost',
                   'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}
        with patch('asyncpg.create_pool', new=AsyncMock()) as mock_create:
            p1 = await TenantConnectionPool.get('tenant_a', info_a)
            p2 = await TenantConnectionPool.get('tenant_a', info_a)
            assert p1 is p2
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_different_tenants_get_different_pools(self):
        info_a = {'db_name': 'tenant_a', 'db_host': 'localhost',
                   'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}
        info_b = {'db_name': 'tenant_b', 'db_host': 'localhost',
                   'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}
        with patch('asyncpg.create_pool', new=AsyncMock()) as mock_create:
            mock_create.side_effect = [AsyncMock(), AsyncMock()]
            p1 = await TenantConnectionPool.get('tenant_a', info_a)
            p2 = await TenantConnectionPool.get('tenant_b', info_b)
            assert p1 is not p2
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        TenantConnectionPool._max_pools = 2
        generic = {'db_name': 't', 'db_host': 'localhost',
                    'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}

        with patch('asyncpg.create_pool', new=AsyncMock()) as mock_create:
            mock_create.side_effect = [AsyncMock(), AsyncMock(), AsyncMock()]
            await TenantConnectionPool.get('t1', {**generic, 'db_name': 't1'})
            await TenantConnectionPool.get('t2', {**generic, 'db_name': 't2'})
            await TenantConnectionPool.get('t3', {**generic, 'db_name': 't3'})
            import asyncio
            await asyncio.sleep(0)

            assert len(TenantConnectionPool._pools) == 2
            assert 't1' not in TenantConnectionPool._pools or 't2' not in TenantConnectionPool._pools

    @pytest.mark.asyncio
    async def test_close_removes_pool(self):
        generic = {'db_name': 't', 'db_host': 'localhost',
                    'db_port': 5432, 'db_user': 'u', 'db_password': 'p'}
        with patch('asyncpg.create_pool', new=AsyncMock()):
            await TenantConnectionPool.get('my-tenant', generic)
            assert 'my-tenant' in TenantConnectionPool._pools
            await TenantConnectionPool.close('my-tenant')
            assert 'my-tenant' not in TenantConnectionPool._pools


class TestTenantJWT:
    def test_token_contains_tenant_claim(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token(
                {'id': 1, 'admin': False, 'tenant': 'clinic-a'},
                expire={'minutes': 60},
            )
        import jwt
        from api.jwt_keys import get_public_key_pem
        payload = jwt.decode(token, get_public_key_pem(), algorithms=['RS256'])
        assert payload['tenant'] == 'clinic-a'

    def test_refresh_preserves_tenant(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            user = {'id': 1, 'admin': False, 'tenant': 'clinic-a'}
            access, refresh = create_token_pair(user)

        from api.users import RefreshToken
        app = Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
        )
        client = TestClient(app)

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    with patch('api.users.get_conn', return_value=mock_conn):
                        with patch('api.users.Users') as mock_users:
                            mock_users.return_value.get_user_row = AsyncMock(return_value={
                                'id': 1, 'admin': False, 'tenant': 'clinic-a',
                                'status': 'active', 'token_version': 0,
                            })
                            mock_users.return_value.get_user_role = AsyncMock(return_value=(
                                'receptionist', ['REGISTRATION_READ', 'QUEUE_READ'],
                            ))
                            resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 200
            payload = verify_token(resp.json()['access_token'])
            assert payload['tenant'] == 'clinic-a'
            # Refresh must mint from current DB state, not stale claims (R2-01).
            assert payload['role'] == 'receptionist'
            assert payload['permissions'] == ['REGISTRATION_READ', 'QUEUE_READ']

    def test_refresh_inactive_user_denied(self):
        from api.users import RefreshToken
        app = Starlette(
            routes=[Route('/api/auth/refresh', endpoint=RefreshToken)],
        )
        client = TestClient(app)

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with patch('api.tokens.config', {'secret': SECRET}):
            user = {'id': 1, 'admin': False, 'tenant': 'clinic-a'}
            _, refresh = create_token_pair(user)
        with patch('api.tokens.config', {'secret': SECRET}):
            with patch('api.users.is_blocked', new=AsyncMock(return_value=False)):
                with patch('api.users.block_token', new=AsyncMock()):
                    with patch('api.users.get_conn', return_value=mock_conn):
                        with patch('api.users.Users') as mock_users:
                            mock_users.return_value.get_user_row = AsyncMock(return_value={
                                'id': 1, 'admin': False, 'tenant': 'clinic-a',
                                'status': 'disabled', 'token_version': 0,
                            })
                            resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})

            assert resp.status_code == 401

    def test_user_can_access_own_tenant(self):
        u = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        assert u.can_access_tenant('my-clinic') is True
        assert u.can_access_tenant('other-clinic') is False

    def test_admin_can_access_any(self):
        u = User({'id': 1, 'admin': True})
        assert u.can_access_tenant('any-clinic') is True

    def test_no_tenant_denied_all(self):
        u = User({'id': 3, 'admin': False})
        assert u.can_access_tenant('some-clinic') is False
