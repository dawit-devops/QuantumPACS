"""R2-03 user_tenant_grants table + async tenant-access gateway tests."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import User, can_access_tenant
from db.user_tenant_grants import UserTenantGrants


def _conn(fetchval_value=None):
    conn = AsyncMock()
    conn.fetchval.return_value = fetchval_value
    return conn


def _await(coro):
    return asyncio.run(coro)


class TestUserTenantGrants:
    def test_has_true_when_row_exists(self):
        conn = _conn(fetchval_value=1)
        assert _await(UserTenantGrants(conn).has(1, 'other-clinic')) is True

    def test_has_false_when_no_row(self):
        conn = _conn(fetchval_value=None)
        assert _await(UserTenantGrants(conn).has(1, 'other-clinic')) is False

    def test_has_coerces_string_user_id_to_int(self):
        conn = _conn(fetchval_value=1)
        _await(UserTenantGrants(conn).has('7', 'other-clinic'))
        sql = conn.fetchval.call_args.args[0]
        assert '"user_id"=7' in sql
        assert "'7'" not in sql

    def test_add_is_idempotent_on_conflict(self):
        conn = _conn()
        _await(UserTenantGrants(conn).add(7, 'other-clinic', created_by='5'))
        sql = conn.execute.call_args.args[0]
        assert 'INSERT INTO "user_tenant_grants"' in sql
        assert 'ON CONFLICT ("user_id", "tenant_slug")' in sql
        assert 'DO NOTHING' in sql

    def test_remove_deletes_row(self):
        conn = _conn()
        _await(UserTenantGrants(conn).remove(7, 'other-clinic'))
        sql = conn.execute.call_args.args[0]
        assert 'DELETE FROM "user_tenant_grants"' in sql
        assert '"user_id"=7' in sql

    def test_list_for_user_selects_slugs(self):
        conn = _conn()
        rows = [{'tenant_slug': 'a', 'scope': 'read', 'created_at': None},
                {'tenant_slug': 'b', 'scope': 'read', 'created_at': None}]
        conn.fetch.return_value = rows
        out = _await(UserTenantGrants(conn).list_for_user('7'))
        assert out == rows
        assert 'tenant_slug' in conn.fetch.call_args.args[0]

    def test_list_for_tenant(self):
        conn = _conn()
        conn.fetch.return_value = [{'user_id': 7, 'created_by': '5', 'created_at': None}]
        out = _await(UserTenantGrants(conn).list_for_tenant('other-clinic'))
        assert len(out) == 1
        assert out[0]['user_id'] == 7


class TestAsyncCanAccessTenant:
    def test_no_slug_always_allowed(self):
        user = User({'id': 1, 'admin': False})
        assert _await(can_access_tenant(user, None)) is True

    def test_admin_any_tenant(self):
        user = User({'id': 1, 'admin': True})
        assert _await(can_access_tenant(user, 'any-clinic')) is True

    def test_home_tenant_allowed_without_grant_lookup(self):
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        with patch.object(User, 'has_grant') as mock_grant:
            assert _await(can_access_tenant(user, 'my-clinic')) is True
            mock_grant.assert_not_called()

    def test_other_tenant_denied_without_permission(self):
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['STUDY_READ']})
        with patch.object(User, 'has_grant') as mock_grant:
            assert _await(can_access_tenant(user, 'other-clinic')) is False
            mock_grant.assert_not_called()

    def test_other_tenant_allowed_with_permission_and_grant(self):
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        with patch.object(User, 'has_grant',
                          new=AsyncMock(return_value=True)) as mock_grant:
            assert _await(can_access_tenant(user, 'other-clinic')) is True
            mock_grant.assert_awaited_once_with('other-clinic')

    def test_other_tenant_denied_with_permission_but_no_grant(self):
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        with patch.object(User, 'has_grant',
                          new=AsyncMock(return_value=False)) as mock_grant:
            assert _await(can_access_tenant(user, 'other-clinic')) is False
            mock_grant.assert_awaited_once_with('other-clinic')


@pytest.mark.asyncio
async def test_has_grant_queries_main_conn():
    user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic'})
    ctx = AsyncMock()
    conn = AsyncMock()
    conn.fetchval.return_value = 1
    ctx.__aenter__.return_value = conn
    with patch('api.auth.get_conn', return_value=ctx):
        assert await user.has_grant('other-clinic') is True
    sql = conn.fetchval.call_args.args[0]
    assert 'user_tenant_grants' in sql