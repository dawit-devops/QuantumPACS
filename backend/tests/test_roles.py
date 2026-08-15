from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import BUILT_IN_ROLES
from api.roles import RoleUsersHandler, RolesHandler
from api.validate import validation_exception_handler, _ValidationException
from db.roles import Roles


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({
            'id': 1, 'admin': True, 'permissions': ['ROLE_READ'], 'role': 'super_admin',
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
        routes=[
            Route('/roles', endpoint=RolesHandler),
            Route('/roles/{id}/users', endpoint=RoleUsersHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestRoles:
    @pytest.mark.asyncio
    async def test_get_all_returns_list(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': '1', 'name': 'Admin', 'slug': 'admin', 'permissions': '["FILE_READ"]', 'built_in': True},
            {'id': '2', 'name': 'Viewer', 'slug': 'viewer', 'permissions': '[]', 'built_in': False},
        ]
        r = Roles(conn=conn)
        result = await r.get_all()
        assert len(result) == 2
        assert result[0]['name'] == 'Admin'
        assert isinstance(result[0]['permissions'], list)

    @pytest.mark.asyncio
    async def test_get_returns_role(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'abc-123', 'name': 'Admin', 'slug': 'admin',
            'permissions': '["FILE_READ"]', 'built_in': True,
        }
        r = Roles(conn=conn)
        result = await r.get('abc-123')
        assert result['slug'] == 'admin'
        assert result['permissions'] == ['FILE_READ']

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        r = Roles(conn=conn)
        result = await r.get('missing-id')
        assert result is None

    @pytest.mark.asyncio
    async def test_create_returns_id(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'new-id-456'
        r = Roles(conn=conn)
        role_id = await r.create('Custom Role', 'custom', ['FILE_READ'])
        assert role_id == 'new-id-456'
        sql = conn.fetchval.call_args[0][0]
        assert 'INSERT INTO' in sql

    @pytest.mark.asyncio
    async def test_patch_updates_fields(self):
        conn = AsyncMock()
        r = Roles(conn=conn)
        await r.patch('role-1', {'name': 'Updated', 'permissions': ['FILE_WRITE']})
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert 'updated_at' in sql

    @pytest.mark.asyncio
    async def test_delete_removes_role(self):
        conn = AsyncMock()
        r = Roles(conn=conn)
        await r.delete('role-1')
        sql = conn.execute.call_args[0][0]
        assert 'DELETE' in sql

    @pytest.mark.asyncio
    async def test_seed_built_in_roles_inserts_all(self):
        conn = AsyncMock()
        # Editable built-ins are probed with fetchrow first (technologist
        # review P0-1 reconcile): row absent -> INSERT, present & superset ->
        # UPDATE, present & subset/edit -> untouched. An empty result means
        # every editable slug is inserted.
        conn.fetchrow = AsyncMock(return_value=None)
        r = Roles(conn=conn)
        await r.seed_built_in_roles()
        calls = conn.execute.call_args_list
        assert len(calls) == len(BUILT_IN_ROLES)
        sql = calls[0][0][0]
        args = calls[0][0][1:]
        assert 'INSERT INTO' in sql
        assert 'super_admin' in args
        slugs = [c[0][1] for c in calls]
        assert 'cashier' in slugs
        # The R2-16 catalog has exactly 14 slugs — any dead role here is a
        # leftover that migration 052 deleted.
        assert set(slugs) == set(BUILT_IN_ROLES)

    @pytest.mark.asyncio
    async def test_role_users_uses_status_column(self):
        """P2-5 regression: RoleUsersHandler queried a nonexistent users.active
        column and 500'd — the modal now reads users.status."""
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {'id': 7, 'username': 'jdoe', 'admin': False, 'status': 'active'},
        ])
        with patch('api.roles.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )):
            client = TestClient(_make_app())
            resp = client.get('/roles/r1/users')
        assert resp.status_code == 200
        sql = conn.fetch.call_args[0][0]
        assert 'status' in sql
        assert 'active' not in sql.split('WHERE')[0]
        data = resp.json()['data']
        assert data[0]['status'] == 'active'

    def test_roles_list_marks_immutable_tiers_unmodifiable(self):
        """P2-3 (tenant_admin review): the Roles page needs to know which rows
        the caller can actually modify, so it can show a lock instead of
        inviting a 403 — immutable anchors stay locked below the platform
        admin, platform-only tiers lock for tenant-scoped admins."""
        conn = MagicMock()
        conn.fetch = AsyncMock(return_value=[
            {'id': '1', 'name': 'Super Admin', 'slug': 'super_admin', 'permissions': '[]', 'built_in': True, 'user_count': 1},
            {'id': '2', 'name': 'Teleradiologist', 'slug': 'teleradiologist', 'permissions': '[]', 'built_in': True, 'user_count': 0},
            {'id': '3', 'name': 'Custom', 'slug': 'custom_reader', 'permissions': '[]', 'built_in': False, 'user_count': 0},
        ])
        user = User({'id': 5, 'admin': False, 'tenant': 'default',
                     'permissions': ['ROLE_READ'], 'role': 'tenant_admin'})
        with patch('api.roles.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )):
            # tenant-scoped admin: super_admin anchor + teleradiologist locked
            client = TestClient(_make_app(user=user))
            resp = client.get('/roles')
        assert resp.status_code == 200
        by_slug = {r['slug']: r for r in resp.json()['data']}
        assert by_slug['super_admin']['modifiable'] is False
        assert by_slug['teleradiologist']['modifiable'] is False
        assert by_slug['custom_reader']['modifiable'] is True

    def test_roles_list_platform_admin_can_modify_platform_tier(self):
        """P2-3: the platform admin bypasses the platform-only tier lock (the
        teleradiologist row becomes modifiable for them)."""
        conn = MagicMock()
        conn.fetch = AsyncMock(return_value=[
            {'id': '2', 'name': 'Teleradiologist', 'slug': 'teleradiologist', 'permissions': '[]', 'built_in': True, 'user_count': 0},
        ])
        with patch('api.roles.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )):
            client = TestClient(_make_app())
            resp = client.get('/roles')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['modifiable'] is True

    @pytest.mark.asyncio
    async def test_seed_built_in_roles_upserts_immutable_and_noops_editable(self):
        conn = AsyncMock()
        r = Roles(conn=conn)
        await r.seed_built_in_roles()
        from api.permissions import IMMUTABLE_ROLE_SLUGS
        sql_by_slug = {c[0][1]: c[0][0] for c in conn.execute.call_args_list}
        # Immutable anchors keep the repair upsert...
        for slug in IMMUTABLE_ROLE_SLUGS:
            assert 'DO UPDATE' in sql_by_slug[slug]
        # ...editable built-ins (incl. platform-only teleradiologist) seed only
        # when absent, so tenant/platform edits survive every boot.
        for slug, sql in sql_by_slug.items():
            if slug not in IMMUTABLE_ROLE_SLUGS:
                assert 'DO NOTHING' in sql
