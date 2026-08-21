import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.audit_log import AuditLog


class TestAuditLogEvent:
    @pytest.mark.asyncio
    async def test_log_event_creates_correct_json_structure(self):
        conn = AsyncMock()
        audit = AuditLog(conn)

        await audit.log_event(
            event_type='user.provisioned',
            actor_id=42,
            resource_type='user',
            resource_id=42,
            details={'oauth_sub': 'sub123'},
            tenant='hospital-a',
            request_id='req-456',
        )

        sql = conn.execute.call_args[0][0]
        assert 'INSERT' in sql and 'logs' in sql

        args = conn.execute.call_args[0]
        payload = args[1]
        assert '"event": "user.provisioned"' in payload
        assert '"actor": 42' in payload
        assert '"resource": {"type": "user", "id": 42}' in payload
        assert '"detail": {"oauth_sub": "sub123"}' in payload
        assert '"tenant": "hospital-a"' in payload
        assert '"request_id": "req-456"' in payload
        assert 'trace_id' in sql
        assert args[2] == 'hospital-a'
        assert args[3] == 'req-456'

    @pytest.mark.asyncio
    async def test_log_event_uses_request_id_var_when_not_provided(self):
        conn = AsyncMock()
        audit = AuditLog(conn)

        with patch('db.audit_log.request_id_var') as mock_rid:
            mock_rid.get.return_value = 'ctx-request-999'
            await audit.log_event(
                event_type='user.login',
                actor_id=1,
                resource_type='session',
                resource_id='sess-1',
            )

        payload = conn.execute.call_args[0][1]
        assert '"request_id": "ctx-request-999"' in payload


class TestAuditLogQuery:
    @pytest.mark.asyncio
    async def test_query_filters_by_tenant(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 1, 'log': '{"event": "test"}', 'tenant': 'hospital-a',
             'created': '2026-01-01', 'trace_id': 't1'},
        ]
        audit = AuditLog(conn)

        result = await audit.query(tenant='hospital-a')
        assert len(result) == 1
        sql = conn.fetch.call_args[0][0]
        assert 'WHERE' in sql.upper() or 'where' in sql.lower()
        assert 'hospital-a' in conn.fetch.call_args[0][1]

    @pytest.mark.asyncio
    async def test_query_filters_by_event_type(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 2, 'log': '{"event": "role.created"}', 'tenant': None,
             'created': '2026-01-01', 'trace_id': 't2'},
        ]
        audit = AuditLog(conn)

        result = await audit.query(event_type='role.created')
        assert len(result) == 1
        assert 'role.created' in conn.fetch.call_args[0][1]

    @pytest.mark.asyncio
    async def test_query_filters_by_actor_id(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {'id': 3, 'log': '{"event": "test", "actor": 99}', 'tenant': None,
             'created': '2026-01-01', 'trace_id': 't3'},
        ]
        audit = AuditLog(conn)

        result = await audit.query(actor_id=99)
        assert len(result) == 1
        sql = conn.fetch.call_args[0][0]
        assert 'actor' in sql
        assert '99' in conn.fetch.call_args[0][1]

    @pytest.mark.asyncio
    async def test_query_combines_all_filters(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        audit = AuditLog(conn)

        await audit.query(tenant='t1', event_type='e1', actor_id=1, limit=10, offset=5)
        sql = conn.fetch.call_args[0][0]
        params = conn.fetch.call_args[0][1:]
        assert 't1' in params
        assert 'e1' in params
        assert '1' in params
        assert 'actor' in sql
        assert 'LIMIT' in sql.upper()
        assert 'OFFSET' in sql.upper()

    @pytest.mark.asyncio
    async def test_count_returns_total(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 7
        audit = AuditLog(conn)

        total = await audit.count(tenant='hospital-a')
        assert total == 7
        sql = conn.fetchval.call_args[0][0]
        assert 'COUNT' in sql.upper()
        assert 'hospital-a' in conn.fetchval.call_args[0][1]


class TestAuditHooks:
    @pytest.mark.asyncio
    async def test_user_provisioned_hook(self):
        from api.oauth import _find_or_create_user

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.return_value = 99

        ctx = AsyncMock()
        ctx.__aenter__.return_value = mock_conn
        ctx.__aexit__.return_value = None

        with (
            patch('api.oauth.get_conn', return_value=ctx),
            patch('api.oauth.Users') as mock_users_cls,
            patch('api.oauth.AuditLog') as mock_audit_cls,
        ):
            mock_users_cls.table = MagicMock()
            mock_users_cls.table.oauth_sub = MagicMock()
            mock_instance = MagicMock()
            mock_instance.select.return_value.where.return_value = MagicMock()
            mock_users_cls.return_value = mock_instance

            mock_audit_instance = MagicMock()
            mock_audit_instance.log_event = AsyncMock()
            mock_audit_cls.return_value = mock_audit_instance

            await _find_or_create_user(
                'sub-abc', 'user@test.com', 'Test User',
                {'slug': 'provider-x'},
            )

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'user.provisioned'
            assert call_kwargs['resource_type'] == 'user'
            assert call_kwargs['resource_id'] == 99

    @pytest.mark.asyncio
    async def test_tenant_provisioned_hook(self):
        from api.tenants import TenantsHandler
        from api.permissions import Permission

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.side_effect = ['new-tenant-uuid']

        mock_audit_instance = MagicMock()
        mock_audit_instance.log_event = AsyncMock()

        request = MagicMock()
        request.method = 'POST'
        request.path_params = {}
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.permissions = [Permission.TENANT_ADMIN.value]
        request.user.tenant = None
        request._body = json.dumps({
            'name': 'New Hospital', 'slug': 'new-hosp',
            'db_name': 'new_hosp', 'db_host': '127.0.0.1', 'db_port': 5432,
            'db_user': 'admin', 'db_password': 'pass', 'storage_quota_bytes': 0,
        }).encode()
        request.scope = {'type': 'http', 'path': '/api/tenants', 'method': 'POST'}
        request.query_params = {}

        handler = TenantsHandler(request.scope, AsyncMock(), AsyncMock())

        with (
            patch('api.tenants.get_conn', return_value=mock_conn),
            patch('api.tenants.config', {}),
            patch('api.tenants.AuditLog', return_value=mock_audit_instance),
            patch('api.tenants.TenantProvisioner.provision',
                  new=AsyncMock(return_value={'tenant_id': 'mock-id', 'admin_password': 'test-pass'})),
        ):
            resp = await handler.post(request)
            assert resp.status_code == 201

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'tenant.provisioned'
            assert call_kwargs['resource_type'] == 'tenant'
            assert call_kwargs['tenant'] == 'new-hosp'

    @pytest.mark.asyncio
    async def test_tenant_deleted_hook(self):
        from api.tenants import TenantHandler
        from api.permissions import Permission

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None
        mock_conn.fetchrow.return_value = {
            'id': 'tenant-1', 'name': 'Old Hosp', 'slug': 'old-hosp',
            'db_name': 'old_hosp',
        }

        mock_audit_instance = MagicMock()
        mock_audit_instance.log_event = AsyncMock()

        request = MagicMock()
        request.method = 'DELETE'
        request.path_params = {'id': 'tenant-1'}
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.permissions = [Permission.TENANT_ADMIN.value]
        request.user.tenant = None
        request.scope = {'type': 'http', 'path': '/api/tenants/tenant-1', 'method': 'DELETE'}
        request.query_params = {}

        handler = TenantHandler(request.scope, AsyncMock(), AsyncMock())

        with (
            patch('api.tenants.get_conn', return_value=mock_conn),
            patch('api.tenants.AuditLog', return_value=mock_audit_instance),
        ):
            resp = await handler.delete(request)
            assert resp.status_code == 200

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'tenant.deleted'
            assert call_kwargs['resource_id'] == 'tenant-1'

    @pytest.mark.asyncio
    async def test_role_created_hook(self):
        from api.roles import RolesHandler
        from api.permissions import Permission

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None
        mock_conn.fetchval.return_value = 'role-new-id'

        mock_audit_instance = MagicMock()
        mock_audit_instance.log_event = AsyncMock()

        request = MagicMock()
        request.method = 'POST'
        request.path_params = {}
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.permissions = [Permission.ROLE_WRITE.value]
        request.user.tenant = None
        request._body = json.dumps(
            {'name': 'Editor', 'slug': 'editor', 'permissions': ['FILE_READ']}
        ).encode()
        request.scope = {'type': 'http', 'path': '/api/roles', 'method': 'POST'}
        request.query_params = {}

        handler = RolesHandler(request.scope, AsyncMock(), AsyncMock())

        with (
            patch('api.roles.get_conn', return_value=mock_conn),
            patch('api.roles.AuditLog', return_value=mock_audit_instance),
        ):
            resp = await handler.post(request)
            assert resp.status_code == 201

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'role.created'

    @pytest.mark.asyncio
    async def test_role_updated_hook(self):
        from api.roles import RoleHandler
        from api.permissions import Permission

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None
        mock_conn.fetchrow.return_value = {
            'id': 'role-1', 'name': 'Editor', 'slug': 'editor',
            'permissions': '[]', 'built_in': False,
        }

        mock_audit_instance = MagicMock()
        mock_audit_instance.log_event = AsyncMock()

        request = MagicMock()
        request.method = 'PUT'
        request.path_params = {'id': 'role-1'}
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.permissions = [Permission.ROLE_WRITE.value]
        request.user.tenant = None
        request.json = AsyncMock(return_value={'name': 'Editor V2'})
        request._body = json.dumps({'name': 'Editor V2'}).encode()
        request.scope = {'type': 'http', 'path': '/api/roles/role-1', 'method': 'PUT'}
        request.query_params = {}

        handler = RoleHandler(request.scope, AsyncMock(), AsyncMock())

        with (
            patch('api.roles.get_conn', return_value=mock_conn),
            patch('api.roles.AuditLog', return_value=mock_audit_instance),
        ):
            resp = await handler.put(request)
            assert resp.status_code == 200

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'role.updated'
            assert call_kwargs['resource_id'] == 'role-1'

    @pytest.mark.asyncio
    async def test_role_deleted_hook(self):
        from api.roles import RoleHandler
        from api.permissions import Permission

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None
        mock_conn.fetchrow.return_value = {
            'id': 'role-1', 'name': 'Editor', 'slug': 'editor',
            'permissions': '[]', 'built_in': False,
        }

        mock_audit_instance = MagicMock()
        mock_audit_instance.log_event = AsyncMock()

        request = MagicMock()
        request.method = 'DELETE'
        request.path_params = {'id': 'role-1'}
        request.user.is_authenticated = True
        request.user.id = 1
        request.user.permissions = [Permission.ROLE_DELETE.value]
        request.user.tenant = None
        request.scope = {'type': 'http', 'path': '/api/roles/role-1', 'method': 'DELETE'}
        request.query_params = {}

        handler = RoleHandler(request.scope, AsyncMock(), AsyncMock())

        with (
            patch('api.roles.get_conn', return_value=mock_conn),
            patch('api.roles.AuditLog', return_value=mock_audit_instance),
        ):
            resp = await handler.delete(request)
            assert resp.status_code == 200

            mock_audit_instance.log_event.assert_awaited_once()
            call_kwargs = mock_audit_instance.log_event.call_args.kwargs
            assert call_kwargs['event_type'] == 'role.deleted'


class TestRisBillingAuditCompleteness:
    """S12-11: every RIS write event must be audited — charge drop and claim
    submit both log to audit_log, not just mutate the table."""

    @pytest.mark.asyncio
    async def test_charge_drop_writes_audit_event(self):
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import User
        from api.billing import RisChargeDropHandler

        audit_events = []

        class _FakeAudit:
            def __init__(self, conn):
                pass

            async def log_event(self, **kwargs):
                audit_events.append(kwargs)

        class _FakeAuth(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.scope['user'] = User(
                    {'id': 1, 'permissions': ['BILLING_WRITE'], 'tenant': 'default'})
                request.scope['auth'] = None
                return await call_next(request)

        class _FakeConn:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                return False

            async def execute(self, sql, *args):
                return 'OK'

            async def fetchrow(self, sql, *args):
                if 'UPDATE ris_charges' in sql:
                    return {'id': 'chg-1', 'status': 'BILLED'}
                return {'id': 'chg-1', 'status': 'PENDING', 'created_at': None}

        app = Starlette(
            routes=[Route('/ris/billing/charges/{id}/drop',
                          endpoint=RisChargeDropHandler, methods=['POST'])],
            middleware=[Middleware(_FakeAuth)],
        )
        client = TestClient(app)

        with patch('api.billing.get_conn', return_value=_FakeConn()), \
             patch('db.audit_log.AuditLog', _FakeAudit), \
             patch('api.billing.effective_tenant', return_value='default'), \
             patch('api.billing._unbilled_count', return_value=0):
            resp = client.post('/ris/billing/charges/chg-1/drop')

        assert resp.status_code == 200, resp.text
        assert audit_events, 'charge drop must write an audit event'
        assert audit_events[0]['event_type'] == 'billing.charge_dropped'
        assert audit_events[0]['resource_id'] == 'chg-1'
        assert audit_events[0]['resource_type'] == 'ris_charges'
