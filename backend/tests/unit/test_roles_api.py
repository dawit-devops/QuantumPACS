from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.roles import RolesHandler, RoleHandler
from api.permissions import Permission


class MockConn:
    def __init__(self):
        self.fetch = AsyncMock(return_value=[])
        self.fetchrow = AsyncMock(return_value=None)
        self.fetchval = AsyncMock(return_value='new-id')
        self.execute = AsyncMock()
        self._transaction_ctx = AsyncMock()
        self._transaction_ctx.__aenter__ = AsyncMock(return_value=self)
        self._transaction_ctx.__aexit__ = AsyncMock(return_value=None)
        self.transaction = MagicMock(return_value=self._transaction_ctx)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


def make_request(method='GET', path='/roles', params=None, body=None, permissions=None):
    request = MagicMock()
    request.method = method
    request.path_params = params or {}
    request.user.is_authenticated = True
    request.user.id = 1
    request.user.tenant = None
    request.user.permissions = permissions or []
    request.json = AsyncMock(return_value=body or {})
    request.scope = {'type': 'http', 'path': path, 'method': method}
    return request


def make_handler(cls, request):
    return cls(request.scope, AsyncMock(), AsyncMock())


class TestRolesHandler:
    @pytest.mark.asyncio
    async def test_get_all_returns_ok(self):
        conn = MockConn()
        request = make_request(permissions=[Permission.ROLE_READ.value])
        handler = make_handler(RolesHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.get(request)
        assert resp.status_code == 200
        data = resp.body
        assert b'data' in data

    @pytest.mark.asyncio
    async def test_get_all_requires_role_read(self):
        conn = MockConn()
        request = make_request(permissions=[Permission.FILE_READ.value])
        handler = make_handler(RolesHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.get(request)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_returns_created(self):
        conn = MockConn()
        body = {'name': 'Test Role', 'slug': 'test', 'permissions': ['FILE_READ']}
        request = make_request(method='POST', body=body, permissions=[Permission.ROLE_WRITE.value])
        handler = make_handler(RolesHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.post(request)
        assert resp.status_code == 201
        data = resp.body
        assert b'id' in data

    @pytest.mark.asyncio
    async def test_create_requires_role_write(self):
        conn = MockConn()
        body = {'name': 'Test Role', 'slug': 'test', 'permissions': ['FILE_READ']}
        request = make_request(method='POST', body=body, permissions=[Permission.ROLE_READ.value])
        handler = make_handler(RolesHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.post(request)
        assert resp.status_code == 403


class TestRoleHandler:
    @pytest.mark.asyncio
    async def test_get_returns_role(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 'r1', 'name': 'Admin', 'slug': 'admin',
            'permissions': '["FILE_READ"]', 'built_in': True, 'tenant_id': None,
        })
        request = make_request(params={'id': 'r1'}, permissions=[Permission.ROLE_READ.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.get(request)
        assert resp.status_code == 200
        assert b'admin' in resp.body

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value=None)
        request = make_request(params={'id': 'missing'}, permissions=[Permission.ROLE_READ.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.get(request)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_built_in_role_blocked(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 'r1', 'name': 'Admin', 'slug': 'admin',
            'permissions': '[]', 'built_in': True, 'tenant_id': None,
        })
        request = make_request(method='DELETE', params={'id': 'r1'}, permissions=[Permission.ROLE_DELETE.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.delete(request)
        assert resp.status_code == 200
        assert b'error' in resp.body

    @pytest.mark.asyncio
    async def test_delete_custom_role_succeeds(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 'r2', 'name': 'Custom', 'slug': 'custom',
            'permissions': '[]', 'built_in': False, 'tenant_id': None,
        })
        request = make_request(method='DELETE', params={'id': 'r2'}, permissions=[Permission.ROLE_DELETE.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.delete(request)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_requires_delete_permission(self):
        conn = MockConn()
        request = make_request(method='DELETE', params={'id': 'r1'}, permissions=[Permission.ROLE_READ.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.delete(request)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_put_updates_role(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 'r1', 'name': 'Admin', 'slug': 'admin',
            'permissions': '["FILE_READ"]', 'built_in': True, 'tenant_id': None,
        })
        body = {'name': 'Updated', 'permissions': ['FILE_WRITE']}
        request = make_request(method='PUT', params={'id': 'r1'}, body=body, permissions=[Permission.ROLE_WRITE.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.put(request)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_put_not_found(self):
        conn = MockConn()
        conn.fetchrow = AsyncMock(return_value=None)
        body = {'name': 'Nope'}
        request = make_request(method='PUT', params={'id': 'missing'}, body=body, permissions=[Permission.ROLE_WRITE.value])
        handler = make_handler(RoleHandler, request)
        with patch('api.roles.get_conn', return_value=conn):
            resp = await handler.put(request)
        assert resp.status_code == 404
