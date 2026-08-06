import sys
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.files import Upload
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': [
            'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
        ]})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


class _TenantState(BaseHTTPMiddleware):
    """Injects request.state attributes the way TenantMiddleware would."""

    def __init__(self, app, state=None):
        super().__init__(app)
        self._state = state or {}

    async def dispatch(self, request, call_next):
        for key, value in self._state.items():
            setattr(request.state, key, value)
        return await call_next(request)


class _TenantAcquire:
    """Mimics asyncpg Pool.acquire() bound method: callable, async-withable."""

    def __init__(self, used_bytes):
        self.used_bytes = used_bytes

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        conn = MagicMock()
        conn.fetchval = AsyncMock(return_value=self.used_bytes)
        return conn

    async def __aexit__(self, *exc):
        return None


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(tenant_state=None, user=None):
    middleware = [Middleware(_FakeAuth, user=user)]
    if tenant_state:
        middleware.append(Middleware(_TenantState, state=tenant_state))
    return Starlette(
        routes=[Route('/upload', endpoint=Upload)],
        middleware=middleware,
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _upload_patches(mock_conn):
    """Named patch objects; use _enter() to activate and get the mocks."""
    storage = MagicMock()
    storage.copy = AsyncMock(return_value={'location': '/tmp/x'})
    return {
        'parse_dcm': patch('api.files.parse_dcm', return_value={
            'patientid': 'P001', 'studyinstanceuid': 'S001',
            'seriesinstanceuid': 'SE001', 'sopinstanceuid': 'SO001',
            'patient_name': 'Smith^John', 'cleaned': {},
        }),
        'hash_file': patch('api.files.hash_file', return_value='h1'),
        'master': patch('api.files.Replica.master', new_callable=AsyncMock, return_value={'id': 1}),
        'find_by_hash': patch('api.files.Files.find_by_hash', new_callable=AsyncMock, return_value=None),
        'insert': patch('api.files.Files.insert_or_select', new_callable=AsyncMock, return_value={'id': 1}),
        'rf_add': patch('api.files.ReplicaFiles.add', new_callable=AsyncMock),
        'storage': patch('api.files.Storage.get', new_callable=AsyncMock, return_value=storage),
        'broadcast': patch('api.files.broadcast_to_user', new_callable=AsyncMock),
        'notifications': patch('api.files.Notifications.create', new_callable=AsyncMock),
        'notify_role': patch('api.files.notify_role', new_callable=AsyncMock),
        'get_conn': patch(
            'api.files.get_conn',
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            ),
        ),
    }


def _enter(patches):
    """Activate patches; returns (ExitStack, {name: mock})."""
    stack = ExitStack()
    mocks = {name: stack.enter_context(p) for name, p in patches.items()}
    return stack, mocks


def _upload(client, name='IM000001.dcm'):
    # len(content) must be > 132 with b'DICM' at offset 128 to pass _is_dicom
    content = b'\x00' * 128 + b'DICM' + b'\x00' * 64
    resp = client.post('/upload', files={'file': (name, content, 'application/dicom')})
    return resp, content


class TestUploadQuota:
    def test_upload_records_size(self):
        stack, mocks = _enter(_upload_patches(_mock_conn()))
        with stack:
            client = TestClient(_make_app())
            resp, content = _upload(client)
        assert resp.status_code == 200
        file_data = mocks['insert'].await_args.args[0]
        assert file_data['size'] == len(content)
        assert file_data['size'] > 0

    def test_upload_over_quota_rejected(self):
        state = {
            'tenant_slug': 'clinic-alfa',
            'tenant': {'storage_quota_bytes': 100, 'storage_used_bytes': 0},
            'tenant_conn': _TenantAcquire(80),
        }
        stack, mocks = _enter(_upload_patches(_mock_conn()))
        with stack:
            client = TestClient(_make_app(tenant_state=state))
            resp, content = _upload(client)
        assert resp.status_code == 403
        assert resp.json()['error']['code'] == 'QUOTA_EXCEEDED'
        assert str(len(content)) in resp.json()['error']['message']
        mocks['insert'].assert_not_awaited()
        mocks['find_by_hash'].assert_not_awaited()
        mocks['rf_add'].assert_not_awaited()

    def test_upload_no_tenant_skips_quota(self):
        stack, mocks = _enter(_upload_patches(_mock_conn()))
        with stack:
            client = TestClient(_make_app())
            resp, content = _upload(client)
        assert resp.status_code == 200
        assert resp.json() == {'id': 1, 'duplicate': False}
        assert mocks['insert'].await_args.args[0]['size'] == len(content)

    def test_upload_persists_storage_used(self):
        state = {
            'tenant_slug': 'clinic-alfa',
            'tenant': {'storage_quota_bytes': 0, 'storage_used_bytes': 0},
            'tenant_conn': _TenantAcquire(1000),
        }
        stack, mocks = _enter(_upload_patches(_mock_conn()))
        with stack, patch('api.files.Tenants') as mock_tenants:
            mock_tenants.return_value.persist_storage_used = AsyncMock()
            client = TestClient(_make_app(tenant_state=state))
            resp, content = _upload(client)
        assert resp.status_code == 200
        mock_tenants.return_value.persist_storage_used.assert_awaited_once_with(
            'clinic-alfa', 1000 + len(content),
        )
        mocks['notify_role'].assert_not_awaited()

    def test_upload_notifies_super_admins_on_breach(self):
        state = {
            'tenant_slug': 'clinic-alfa',
            'tenant': {'storage_quota_bytes': 1000, 'storage_used_bytes': 0},
            'tenant_conn': _TenantAcquire(800),
        }
        mock_conn = _mock_conn()
        stack, mocks = _enter(_upload_patches(mock_conn))
        with stack, patch('api.files.Tenants') as mock_tenants:
            mock_tenants.return_value.persist_storage_used = AsyncMock()
            client = TestClient(_make_app(tenant_state=state))
            resp, content = _upload(client)
        assert resp.status_code == 200
        mock_tenants.return_value.persist_storage_used.assert_awaited_once_with(
            'clinic-alfa', 800 + len(content),
        )
        mocks['notify_role'].assert_awaited_once()
        args = mocks['notify_role'].await_args.args
        assert args[0] is mock_conn
        assert args[1] == 'super_admin'
        assert args[2] == 'storage.quota_breach'
        assert 'clinic-alfa' in args[3]
        assert args[5] == '/tenants'

    def test_upload_persist_falls_back_to_direct_update(self):
        state = {
            'tenant_slug': 'clinic-alfa',
            'tenant': {'storage_quota_bytes': 0, 'storage_used_bytes': 0},
            'tenant_conn': _TenantAcquire(1000),
        }
        mock_conn = _mock_conn()
        stack, mocks = _enter(_upload_patches(mock_conn))
        with stack, patch('api.files.Tenants') as mock_tenants:
            mock_tenants.return_value.persist_storage_used = None
            client = TestClient(_make_app(tenant_state=state))
            resp, content = _upload(client)
        assert resp.status_code == 200
        mock_conn.execute.assert_awaited_once()
        sql, used, slug = mock_conn.execute.await_args.args
        assert 'UPDATE tenants SET storage_used_bytes' in sql
        assert used == 1000 + len(content)
        assert slug == 'clinic-alfa'

    def test_upload_registry_fallback_when_tenant_conn_missing(self):
        state = {
            'tenant_slug': 'clinic-alfa',
            'tenant': {'storage_quota_bytes': 100, 'storage_used_bytes': 90},
        }
        stack, mocks = _enter(_upload_patches(_mock_conn()))
        with stack, patch('api.files.Tenants') as mock_tenants:
            mock_tenants.return_value.persist_storage_used = AsyncMock()
            client = TestClient(_make_app(tenant_state=state))
            resp, content = _upload(client)
        assert resp.status_code == 403
        assert resp.json()['error']['code'] == 'QUOTA_EXCEEDED'
        mocks['insert'].assert_not_awaited()
