from unittest.mock import AsyncMock, MagicMock

import pytest

from api.rbac import requires_permission, get_role_permissions
from api.permissions import Permission, BUILT_IN_ROLES


class MockRequest:
    def __init__(self, is_authenticated=True, permissions=None):
        self.user = MagicMock()
        self.user.is_authenticated = is_authenticated
        self.user.permissions = permissions or []


class TestRequiresPermission:
    @pytest.mark.asyncio
    async def test_allows_with_correct_permission(self):
        req = MockRequest(permissions=[Permission.FILE_DELETE.value])

        async def handler(_self, r):
            return r.user.permissions[0]

        wrapped = requires_permission(Permission.FILE_DELETE)(handler)

        result = await wrapped(None, req)

        assert result == Permission.FILE_DELETE.value

    @pytest.mark.asyncio
    async def test_denies_without_permission(self):
        req = MockRequest(permissions=[Permission.FILE_READ.value])

        async def handler(_self, r):
            return 'should not reach'

        wrapped = requires_permission(Permission.FILE_DELETE)(handler)

        result = await wrapped(None, req)

        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_denies_unauthenticated(self):
        req = MockRequest(is_authenticated=False, permissions=[])

        async def handler(_self, r):
            return 'should not reach'

        wrapped = requires_permission(Permission.FILE_DELETE)(handler)

        with pytest.raises(Exception) as exc:
            await wrapped(None, req)
        assert '401' in str(exc.value) or 'Not authenticated' in str(exc.value)

    @pytest.mark.asyncio
    async def test_multiple_permissions_correct(self):
        req = MockRequest(permissions=[
            Permission.FILE_READ.value, Permission.FILE_DELETE.value, Permission.PATIENT_WRITE.value,
        ])

        async def handler(_self, r):
            return r.user.permissions

        wrapped = requires_permission(Permission.FILE_DELETE)(handler)

        result = await wrapped(None, req)

        assert Permission.FILE_DELETE.value in result


class TestGetRolePermissions:
    def test_returns_super_admin_permissions(self):
        perms = get_role_permissions('super_admin')
        assert Permission.FILE_DELETE.value in perms

    def test_returns_empty_for_unknown_role(self):
        perms = get_role_permissions('nonexistent_role')
        assert perms == list(BUILT_IN_ROLES.get('cashier', []))

    def test_returns_cashier_for_none(self):
        perms = get_role_permissions(None)
        assert perms == list(BUILT_IN_ROLES.get('cashier', []))

    def test_admin_has_delete_and_admin_permissions(self):
        perms = get_role_permissions('admin')
        assert Permission.FILE_DELETE.value in perms
        assert Permission.USER_WRITE.value in perms


class TestUserCanAccessTenant:
    def test_admin_can_access_any_tenant(self):
        from api.auth import User
        u = User({'id': 1, 'admin': True})
        assert u.can_access_tenant('hospital-a') is True
        assert u.can_access_tenant('clinic-42') is True

    def test_user_can_access_own_tenant(self):
        from api.auth import User
        u = User({'id': 2, 'admin': False, 'tenant': 'hospital-a'})
        assert u.can_access_tenant('hospital-a') is True

    def test_user_cannot_access_other_tenant(self):
        from api.auth import User
        u = User({'id': 2, 'admin': False, 'tenant': 'hospital-a'})
        assert u.can_access_tenant('clinic-42') is False

    def test_user_without_tenant_can_access_no_tenant(self):
        from api.auth import User
        u = User({'id': 3, 'admin': False})
        assert u.can_access_tenant('hospital-a') is False

    def test_access_none_tenant_returns_true(self):
        from api.auth import User
        u = User({'id': 1, 'admin': False, 'tenant': 'hospital-a'})
        assert u.can_access_tenant(None) is True

    def test_tenant_from_jwt_data(self):
        from api.auth import User
        u = User({'id': 4, 'admin': False, 'tenant': 'my-clinic'})
        assert u.tenant == 'my-clinic'
