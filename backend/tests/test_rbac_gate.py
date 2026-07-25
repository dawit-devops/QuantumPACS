from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.rbac import requires_permission
from api.permissions import Permission, BUILT_IN_ROLES
from api.auth import User

from api.response import ok


class FileReadEndpoint(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        return JSONResponse({'ok': True})


class FileWriteEndpoint(HTTPEndpoint):
    @requires_permission(Permission.FILE_WRITE)
    async def get(self, request):
        return JSONResponse({'ok': True})


class UserAdminEndpoint(HTTPEndpoint):
    @requires_permission(Permission.USER_ADMIN)
    async def get(self, request):
        return JSONResponse({'ok': True})


def _make_app(user):
    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Starlette(
        routes=[
            Route('/api/file-read', endpoint=FileReadEndpoint),
            Route('/api/file-write', endpoint=FileWriteEndpoint),
            Route('/api/user-admin', endpoint=UserAdminEndpoint),
        ],
        middleware=[Middleware(FakeAuth)],
    )


class TestPermissionGating:
    def test_user_with_permission_allowed(self):
        user = User({'id': 1, 'admin': False, 'permissions': ['FILE_READ']})
        client = TestClient(_make_app(user))
        resp = client.get('/api/file-read')
        assert resp.status_code == 200

    def test_user_without_permission_denied(self):
        user = User({'id': 1, 'admin': False, 'permissions': ['FILE_WRITE']})
        client = TestClient(_make_app(user))
        resp = client.get('/api/file-read')
        assert resp.status_code == 403

    def test_empty_permissions_denied(self):
        user = User({'id': 1, 'admin': False, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/api/file-read')
        assert resp.status_code == 403

    def test_correct_permission_across_multiple_endpoints(self):
        user = User({'id': 1, 'admin': False,
                      'permissions': ['FILE_READ', 'FILE_WRITE']})
        client = TestClient(_make_app(user))
        assert client.get('/api/file-read').status_code == 200
        assert client.get('/api/file-write').status_code == 200
        assert client.get('/api/user-admin').status_code == 403

    def test_super_admin_has_all_permissions(self):
        user = User({'id': 1, 'admin': True,
                      'permissions': list(BUILT_IN_ROLES['super_admin'])})
        client = TestClient(_make_app(user))
        assert client.get('/api/file-read').status_code == 200
        assert client.get('/api/file-write').status_code == 200
        assert client.get('/api/user-admin').status_code == 200


class TestRoleBasedAccess:
    def test_technologist_has_file_permissions(self):
        perms = BUILT_IN_ROLES['technologist']
        user = User({'id': 2, 'admin': False, 'role': 'technologist',
                      'permissions': perms})
        client = TestClient(_make_app(user))
        assert client.get('/api/file-read').status_code == 200
        assert client.get('/api/file-write').status_code == 200

    def test_cashier_denied_file_write(self):
        perms = BUILT_IN_ROLES['cashier']
        user = User({'id': 3, 'admin': False, 'role': 'cashier',
                      'permissions': perms})
        client = TestClient(_make_app(user))
        resp = client.get('/api/file-write')
        assert resp.status_code == 403

    def test_radiologist_denied_file_write(self):
        perms = BUILT_IN_ROLES['radiologist']
        user = User({'id': 4, 'admin': False, 'role': 'radiologist',
                      'permissions': perms})
        client = TestClient(_make_app(user))
        resp = client.get('/api/file-write')
        assert resp.status_code == 403

    def test_physician_read_only(self):
        perms = BUILT_IN_ROLES['physician']
        user = User({'id': 5, 'admin': False, 'role': 'physician',
                      'permissions': perms})
        client = TestClient(_make_app(user))
        assert client.get('/api/file-read').status_code == 200
        assert client.get('/api/file-write').status_code == 403

    def test_admin_has_user_read_write_but_not_user_admin(self):
        perms = BUILT_IN_ROLES['admin']
        user = User({'id': 6, 'admin': False, 'role': 'admin',
                      'permissions': perms})
        client = TestClient(_make_app(user))
        assert client.get('/api/user-admin').status_code == 403


class TestDecoratorEdgeCases:
    @pytest.mark.asyncio
    async def test_decorator_denies_unauthenticated(self):
        req = MagicMock()
        req.user.is_authenticated = False
        req.user.permissions = []

        async def handler(_self, r):
            return 'ok'

        wrapped = requires_permission(Permission.FILE_READ)(handler)
        with pytest.raises(Exception) as exc:
            await wrapped(None, req)
        assert 'Not authenticated' in str(exc.value)
