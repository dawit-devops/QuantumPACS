from unittest.mock import AsyncMock

import pytest

from db.roles import Roles


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
        r = Roles(conn=conn)
        await r.seed_built_in_roles()
        calls = conn.execute.call_args_list
        assert len(calls) == 8
        sql = calls[0][0][0]
        args = calls[0][0][1:]
        assert 'INSERT INTO' in sql
        assert 'super_admin' in args
        slugs = [c[0][1] for c in calls]
        assert 'qa_team' in slugs

    @pytest.mark.asyncio
    async def test_seed_built_in_roles_uses_upsert(self):
        conn = AsyncMock()
        r = Roles(conn=conn)
        await r.seed_built_in_roles()
        sql = conn.execute.call_args[0][0]
        assert 'ON CONFLICT (slug)' in sql
        assert 'DO UPDATE' in sql
