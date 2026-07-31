from unittest.mock import AsyncMock, MagicMock

import pytest

from db.users import Users, hash_password, rand_pswd
from exceptions import ApiException


class TestUsersUtils:
    def test_hash_password_returns_hex_string(self):
        h = hash_password('test_password')
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_password_with_salt(self):
        salt = b'\x00' * 16
        h = hash_password('password', salt)
        assert isinstance(h, str)

    def test_rand_pswd_length(self):
        for length in [8, 12, 16]:
            p = rand_pswd(length)
            assert len(p) == length

    def test_rand_pswd_uses_correct_chars(self):
        p = rand_pswd(100)
        assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in p)


class TestUsers:
    @pytest.mark.asyncio
    async def test_login_success(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 1, 'username': 'admin', 'password': hash_password('correct'),
            'admin': True, 'status': 'active',
        }
        u = Users(conn=conn)
        result = await u.login('admin', 'correct')
        assert result['username'] == 'admin'

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 1, 'username': 'admin', 'password': hash_password('correct'),
            'admin': True, 'status': 'active',
        }
        u = Users(conn=conn)
        with pytest.raises(ApiException, match='Password is not correct'):
            await u.login('admin', 'wrong')

    @pytest.mark.asyncio
    async def test_login_deactivated_user_raises(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 2, 'username': 'inactive', 'password': hash_password('pwd'),
            'admin': False, 'status': 'deactivated',
        }
        u = Users(conn=conn)
        with pytest.raises(ApiException, match='deactivated'):
            await u.login('inactive', 'pwd')

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_raises(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        u = Users(conn=conn)
        with pytest.raises(ApiException, match='not exists'):
            await u.login('nobody', 'pwd')

    @pytest.mark.asyncio
    async def test_is_active_returns_true_for_active(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'active'
        u = Users(conn=conn)
        assert await u.is_active(1) is True

    @pytest.mark.asyncio
    async def test_is_active_returns_false_for_deactivated(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'deactivated'
        u = Users(conn=conn)
        assert await u.is_active(1) is False

    @pytest.mark.asyncio
    async def test_deactivate_updates_status(self):
        conn = AsyncMock()
        u = Users(conn=conn)
        await u.deactivate(5)
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql
        assert '"users"' in sql

    @pytest.mark.asyncio
    async def test_change_password_updates_password(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'password': hash_password('oldpass', salt=b'\x00' * 16)}
        user = type('User', (), {'id': 3})()
        u = Users(conn=conn)
        await u.change_password(user, 'new_secret', 'oldpass')
        sql = conn.execute.call_args[0][0]
        assert 'UPDATE' in sql

    @pytest.mark.asyncio
    async def test_count_users(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 5
        u = Users(conn=conn)
        total = await u.count_users()
        assert total == 5

    @pytest.mark.asyncio
    async def test_count_users_with_search(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 2
        u = Users(conn=conn)
        total = await u.count_users(username='admin')
        assert total == 2
        sql = conn.fetchval.call_args[0][0]
        assert 'ILIKE' in sql.upper()

    @pytest.mark.asyncio
    async def test_get_user_role_returns_role(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            {'role_id': 1},
            {'slug': 'admin', 'permissions': ['files:read', 'files:write']},
        ]
        u = Users(conn=conn)
        slug, perms = await u.get_user_role(1)
        assert slug == 'admin'
        assert 'files:read' in perms

    @pytest.mark.asyncio
    async def test_get_user_role_no_role_returns_empty(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        u = Users(conn=conn)
        slug, perms = await u.get_user_role(99)
        assert slug is None
        assert perms == []

    @pytest.mark.asyncio
    async def test_get_user_role_role_id_none_returns_empty(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'role_id': None}
        u = Users(conn=conn)
        slug, perms = await u.get_user_role(1)
        assert slug is None
        assert perms == []

    @pytest.mark.asyncio
    async def test_get_users_returns_role_info(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 1, 'username': 'admin', 'admin': True, 'status': 'active',
             'role_name': 'Administrator', 'role_slug': 'admin'},
            {'id': 2, 'username': 'tech1', 'admin': False, 'status': 'active',
             'role_name': 'Technologist', 'role_slug': 'technologist'},
        ]
        u = Users(conn=conn)
        users = await u.get_users()
        assert users[0]['role_name'] == 'Administrator'
        assert users[1]['role_slug'] == 'technologist'
        sql = conn.fetch.call_args[0][0]
        assert 'JOIN' in sql.upper()
        assert 'roles' in sql.lower()

    @pytest.mark.asyncio
    async def test_add_superadmin_assigns_role_id(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        conn.fetchval.return_value = 1
        ctx = AsyncMock()
        conn.transaction = MagicMock(return_value=ctx)
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=None)
        u = Users(conn=conn)
        await u.add_superadmin()
        sql = conn.execute.call_args[0][0]
        assert 'role_id' in sql
        assert 'super_admin' not in sql
