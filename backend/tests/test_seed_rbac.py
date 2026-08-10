"""Unit tests for management.seed_rbac (CI seeds roles + superadmin before boot)."""

from unittest.mock import AsyncMock, patch

import pytest


def test_module_exposes_cli_entrypoints():
    import management.seed_rbac as m

    assert callable(m.main)
    assert callable(m.seed)


@pytest.mark.asyncio
async def test_seed_calls_seed_built_in_roles_and_add_superadmin():
    import management.seed_rbac as m

    conn = _FakeConn()

    with (
        patch('management.seed_rbac.setup', new=AsyncMock()),
        patch('management.seed_rbac.teardown', new=AsyncMock()),
        patch('management.seed_rbac.get_conn', return_value=conn),
        patch('management.seed_rbac.Roles') as roles_cls,
        patch('management.seed_rbac.Users') as users_cls,
    ):
        roles_cls.return_value.seed_built_in_roles = AsyncMock()
        users_cls.return_value.add_superadmin = AsyncMock()
        await m.seed()

    roles_cls.return_value.seed_built_in_roles.assert_awaited_once()
    users_cls.return_value.add_superadmin.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_roles_only_skips_superadmin():
    import management.seed_rbac as m

    conn = _FakeConn()

    with (
        patch('management.seed_rbac.setup', new=AsyncMock()),
        patch('management.seed_rbac.teardown', new=AsyncMock()),
        patch('management.seed_rbac.get_conn', return_value=conn),
        patch('management.seed_rbac.Roles') as roles_cls,
        patch('management.seed_rbac.Users') as users_cls,
    ):
        roles_cls.return_value.seed_built_in_roles = AsyncMock()
        users_cls.return_value.add_superadmin = AsyncMock()
        await m.seed(roles_only=True)

    roles_cls.return_value.seed_built_in_roles.assert_awaited_once()
    users_cls.return_value.add_superadmin.assert_not_awaited()


class _FakeConn:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False
