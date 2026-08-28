"""HI-2 / CR-1 regression tests for the files.tenant guard and ES tenant
tagging (tenant/pacs round-2 implementer)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.files import FileHandler
from db import conn as db_conn
from db.files import Files, set_es_indexer, set_storage_provider


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None, state=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['FILE_READ']})
        self._state = state

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        if self._state is not None:
            # Pre-populate the scope state dict the way TenantMiddleware does,
            # so endpoints can read request.state.tenant_slug.
            request.scope['state'] = self._state
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(user=None, state=None):
    from starlette.exceptions import HTTPException
    from api.validate import validation_exception_handler, _ValidationException
    return Starlette(
        routes=[Route('/api/files/{id}', FileHandler, methods=['GET'])],
        middleware=[Middleware(_FakeAuth, user=user, state=state)],
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
    # transaction() is used as `async with conn.transaction():` — it must
    # return an async CM, not a coroutine (AsyncMock's call protocol).
    conn.transaction = MagicMock()
    conn.transaction.return_value.__aenter__ = AsyncMock(return_value=None)
    conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(conn):
    return patch(
        'api.files.get_conn',
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ),
    )


def _base_filedata():
    return {
        'name': 'a.dcm',
        'hash': 'h',
        'size': 10,
        'cleaned': {'PatientID': 'P1'},
        'patient_id': 'P1',
        'patient_name': 'John Doe',
        'patient_birth_date': '1980-01-01',
        'patient_sex': 'M',
        'study_id': 'S1',
        'study_date': '20260101',
        'series_number': '1',
        'sop_instance_uid': '1.2.3.4.5',
    }


class TestFilesAddTenantColumn:
    """HI-2: the files INSERT carries the owning tenant."""

    @pytest.mark.asyncio
    async def test_add_inserts_tenant_column(self):
        conn = _mock_conn()
        conn.fetchval = AsyncMock(side_effect=[9, 10, 11, 42])
        set_es_indexer(None)
        filedata = {**_base_filedata(), 'tenant': 'acme'}
        await Files(conn).add(filedata)
        insert_sql = str(conn.fetchval.call_args_list[3].args[0])
        assert '"tenant"' in insert_sql
        assert "'acme'" in insert_sql
        assert filedata['id'] == 42

    @pytest.mark.asyncio
    async def test_add_without_tenant_uses_null(self):
        conn = _mock_conn()
        conn.fetchval = AsyncMock(side_effect=[9, 10, 11, 42])
        set_es_indexer(None)
        await Files(conn).add(_base_filedata())
        insert_sql = str(conn.fetchval.call_args_list[3].args[0])
        assert '"tenant"' in insert_sql
        assert 'null' in insert_sql


class TestFilesIndexerTenantTag:
    """CR-1: the direct ES indexer is scoped by the tenant ContextVar."""

    @pytest.mark.asyncio
    async def test_add_passes_contextvar_slug_to_indexer(self):
        conn = _mock_conn()
        conn.fetchval = AsyncMock(side_effect=[9, 10, 11, 42])
        indexer = AsyncMock()
        set_es_indexer(indexer)
        db_conn.set_tenant_slug('acme')
        try:
            await Files(conn).add(_base_filedata())
        finally:
            db_conn.reset_tenant_slug()
            set_es_indexer(None)
        indexer.assert_called_once()
        assert indexer.call_args.kwargs['tenant_slug'] == 'acme'

    @pytest.mark.asyncio
    async def test_delete_passes_contextvar_slug_to_indexer(self):
        conn = _mock_conn()
        conn.fetchrow = AsyncMock(return_value={'id': 1, 'type': 'local'})
        conn.fetchval = AsyncMock(return_value=0)
        set_storage_provider(None)
        indexer = AsyncMock()
        set_es_indexer(indexer)
        db_conn.set_tenant_slug('acme')
        try:
            await Files(conn).delete(file_id=42, master_id=1)
        finally:
            db_conn.reset_tenant_slug()
            set_es_indexer(None)
        indexer.assert_called_once_with(42, delete=True, tenant_slug='acme')


def _fake_tenant_info(slug):
    """Both shared-DB tenants resolve to the main database config — the
    shape uses_main_database() compares against config's db_* values."""
    if slug in ('', None):
        return None
    return {'slug': slug, 'db_name': 'quantumpacs', 'db_host': '127.0.0.1',
            'db_user': 'quantumpacs', 'db_port': 5432,
            'db_password': '974e03eb34f334cc36859c9d910c0dace7f04c60'}


class TestFilesTenantGuard:
    """HI-2: the file get guard now sees the real files.tenant value."""

    @staticmethod
    def _row(**over):
        row = {
            'id': 1, 'name': 'a.dcm',
            'patient_db_id': 2, 'study_db_id': 3, 'series_db_id': 4,
            'patient_id': 'P1', 'study_id': 'S1', 'series_number': '1',
            'meta': None, 'tools_state': None, 'deleted': False, 'size': 7,
            'tenant': None,
            'replica_id': None, 'replica_replica_id': None,
            'replica_file_id': None, 'location': None,
            'replica_status': None, 'replica_meta': None,
        }
        row.update(over)
        return row

    def _get(self, user, row, state=None):
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[row])
        with _patch_get_conn(conn):
            client = TestClient(_make_app(user=user, state=state))
            return client.get('/api/files/1')

    def test_tenant_scoped_get_rejects_other_tenant_row(self):
        # A row tagged 'other-clinic' is outside the 'acme' caller's scope —
        # refused with 404, the same code the middleware returns for unknown
        # tenants, so the permission oracle stays closed.
        user = User({'id': 1, 'tenant': 'acme', 'permissions': ['FILE_READ']})
        resp = self._get(user, self._row(tenant='other-clinic'))
        assert resp.status_code == 404

    def test_same_tenant_row_allowed(self):
        user = User({'id': 1, 'tenant': 'acme', 'permissions': ['FILE_READ']})
        resp = self._get(user, self._row(tenant='acme'))
        assert resp.status_code == 200
        assert resp.json()['tenant'] == 'acme'

    def test_admin_bypasses_guard(self):
        user = User({'id': 1, 'admin': True, 'permissions': ['FILE_READ']})
        resp = self._get(user, self._row(tenant='other-clinic'))
        assert resp.status_code == 200

    def test_unscoped_user_cannot_read_tagged_row(self):
        # A platform user with no tenant scope must not see tenant-tagged
        # files either — the tag makes the file invisible outside its tenant.
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        resp = self._get(user, self._row(tenant='acme'))
        assert resp.status_code == 404

    def test_unscoped_row_stays_readable(self):
        # Untagged (main-store) files keep the historical behaviour.
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        resp = self._get(user, self._row(tenant=None))
        assert resp.status_code == 200

    def test_shared_db_tenant_reads_main_store_row(self):
        # F7: a shared-DB tenant (acme, data store = main database) shares
        # the files table with the seeded 'default'-stamped rows — the guard
        # must not 404 them or no seeded file is ever openable.
        user = User({'id': 1, 'tenant': 'acme', 'permissions': ['FILE_READ']})
        state = {'tenant_slug': 'acme'}
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[self._row(tenant='default')])
        with _patch_get_conn(conn), \
                patch('api.files._tenant_info_async',
                      new=AsyncMock(side_effect=_fake_tenant_info)):
            client = TestClient(_make_app(user=user, state=state))
            resp = client.get('/api/files/1')
        assert resp.status_code == 200

    def test_cross_db_tenant_row_still_refused(self):
        # Tenants with their own database stay strictly separated: an acme
        # caller must never read a row stamped with a foreign tenant slug.
        user = User({'id': 1, 'tenant': 'acme', 'permissions': ['FILE_READ']})
        state = {'tenant_slug': 'acme'}

        async def info(slug):
            if slug == 'acme':
                # acme resolves to its own database (not the main one)
                return {'slug': 'acme', 'db_name': 'acme_db',
                        'db_host': 'db.internal', 'db_user': 'acme_user',
                        'db_port': 5432, 'db_password': 'x'}
            return {'slug': slug, 'db_name': 'quantumpacs',
                    'db_host': '127.0.0.1', 'db_user': 'quantumpacs',
                    'db_port': 5432, 'db_password': '974e03eb'}
        conn = _mock_conn()
        conn.fetch = AsyncMock(return_value=[self._row(tenant='other')])
        with _patch_get_conn(conn), \
                patch('api.files._tenant_info_async', new=info):
            client = TestClient(_make_app(user=user, state=state))
            resp = client.get('/api/files/1')
        assert resp.status_code == 404


class TestUploadTagsRowWithTenant:
    """HI-2: the HTTP upload path stamps the owning tenant on the file_data
    handed to Files.insert_or_select."""

    def _make_upload_app(self, user, state=None):
        from starlette.exceptions import HTTPException
        from api.files import Upload
        from api.validate import validation_exception_handler, _ValidationException
        return Starlette(
            routes=[Route('/api/files', Upload, methods=['POST'])],
            middleware=[Middleware(_FakeAuth, user=user, state=state)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_upload_tags_file_data_with_effective_tenant(self):
        seen = {}

        async def _capture(file_data):
            seen['file_data'] = file_data
            return {'id': 9}

        conn = _mock_conn()
        conn.fetchrow = AsyncMock(
            return_value={'id': 4, 'meta': {}})
        storage = AsyncMock()
        storage.copy = AsyncMock(return_value={'location': '/loc'})

        user = User({'id': 1, 'tenant': 'acme',
                     'permissions': ['FILE_WRITE', 'FILE_READ']})
        client = TestClient(self._make_upload_app(
            user, state={'tenant_slug': 'acme'}))
        with (
            _patch_get_conn(conn),
            patch('api.files.parse_dcm', return_value={
                'patient_id': 'P1', 'study_instance_uid': 'S1',
                'series_instance_uid': 'Se1', 'sop_instance_uid': 'So1'}),
            patch('api.files.hash_file', return_value='hash'),
            patch('api.files._tenant_storage_used',
                  new=AsyncMock(return_value=0)),
            patch('api.files._persist_storage_used', new=AsyncMock()),
            patch('api.files.Storage.get', new=AsyncMock(return_value=storage)),
            patch('api.files.Files') as m_files,
            patch('api.files.ReplicaFiles') as m_rf,
            patch('api.files.Notifications') as m_notif,
            patch('api.files.broadcast_to_user', new=AsyncMock()),
        ):
            m_files.return_value.find_by_hash = AsyncMock(return_value=None)
            m_files.return_value.insert_or_select = AsyncMock(side_effect=_capture)
            m_rf.return_value.add = AsyncMock()
            m_notif.return_value.create = AsyncMock()
            payload = b'\x00' * 128 + b'DICM' + b'\x00' * 124
            resp = client.post(
                '/api/files',
                files={'file': ('a.dcm', payload, 'application/dicom')},
            )

        assert resp.status_code == 200
        assert seen['file_data']['tenant'] == 'acme'
        assert seen['file_data']['size'] == len(payload)
        assert seen['file_data']['hash'] == 'hash'

    def test_platform_upload_keeps_tenant_none(self):

        seen = {}

        async def _capture(file_data):
            seen['file_data'] = file_data
            return {'id': 9}

        conn = _mock_conn()
        conn.fetchrow = AsyncMock(
            return_value={'id': 4, 'meta': {}})
        storage = AsyncMock()
        storage.copy = AsyncMock(return_value={'location': '/loc'})

        user = User({'id': 1, 'permissions': ['FILE_WRITE', 'FILE_READ']})
        client = TestClient(self._make_upload_app(user))
        with (
            _patch_get_conn(conn),
            patch('api.files.parse_dcm', return_value={
                'patient_id': 'P1', 'study_instance_uid': 'S1',
                'series_instance_uid': 'Se1', 'sop_instance_uid': 'So1'}),
            patch('api.files.hash_file', return_value='hash'),
            patch('api.files.Storage.get', new=AsyncMock(return_value=storage)),
            patch('api.files.Files') as m_files,
            patch('api.files.ReplicaFiles') as m_rf,
            patch('api.files.Notifications') as m_notif,
            patch('api.files.broadcast_to_user', new=AsyncMock()),
        ):
            m_files.return_value.find_by_hash = AsyncMock(return_value=None)
            m_files.return_value.insert_or_select = AsyncMock(side_effect=_capture)
            m_rf.return_value.add = AsyncMock()
            m_notif.return_value.create = AsyncMock()
            payload = b'\x00' * 128 + b'DICM' + b'\x00' * 124
            resp = client.post(
                '/api/files',
                files={'file': ('a.dcm', payload, 'application/dicom')},
            )

        assert resp.status_code == 200
        assert seen['file_data']['tenant'] is None


def _make_ctx_app(user):
    """App with the real TenantMiddleware and a scope that echoes the db.conn
    ContextVar slug (what out-of-request helpers like the ES indexer read)."""
    from api.tenant_middleware import TenantMiddleware

    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    async def _ctx(request):
        from starlette.responses import JSONResponse
        return JSONResponse({'slug': db_conn.get_tenant_slug()})

    return Starlette(
        routes=[Route('/api/ctx', endpoint=_ctx)],
        middleware=[Middleware(FakeAuth), Middleware(TenantMiddleware)],
    )


class TestTenantScopeContextVar:
    """The middleware must record the resolved slug in db.conn's ContextVar
    so files ES indexing / deletion can tag by it (CR-1)."""

    def test_claim_scope_sets_conn_slug_contextvar(self):
        mock_info = {'slug': 'my-clinic', 'name': 'My Clinic',
                     'db_name': 'my_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_ctx_app(user))
        with (
            patch('api.tenant_middleware.get_conn') as mock_get_conn,
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            mock_ctx = AsyncMock()
            conn = AsyncMock()
            conn.fetchrow.return_value = mock_info
            mock_ctx.__aenter__.return_value = conn
            mock_get_conn.return_value = mock_ctx
            resp = client.get('/api/ctx')
        assert resp.status_code == 200
        assert resp.json()['slug'] == 'my-clinic'

    def test_unscoped_request_leaves_slug_empty(self):
        user = User({'id': 1, 'admin': True})
        client = TestClient(_make_ctx_app(user))
        resp = client.get('/api/ctx')
        assert resp.status_code == 200
        assert resp.json()['slug'] == ''


class TestTenantAuditMirroredOnTenantPool:
    """N5: cross-tenant gate events are mirrored on the resolved tenant's own
    pool so tenant-scoped log readers see them too."""

    def test_cross_tenant_audit_mirrored_on_tenant_pool(self):
        mock_info = {'slug': 'other-clinic', 'name': 'Other Clinic',
                     'db_name': 'other_clinic'}
        mock_pool = AsyncMock()
        # The middleware calls `async with acquire() as tconn:` — the acquire
        # callable must return an async CM, not a coroutine.
        tconn = AsyncMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            return_value=tconn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(
            return_value=None)
        user = User({'id': 7, 'admin': False, 'tenant': 'my-clinic',
                     'permissions': ['CROSS_TENANT_READ']})
        client = TestClient(_make_ctx_app(user))
        auth_ctx = AsyncMock()
        auth_conn = AsyncMock()
        auth_conn.fetchval.return_value = 1
        auth_ctx.__aenter__.return_value = auth_conn
        mw_ctx = AsyncMock()
        conn = AsyncMock()
        conn.fetchrow.return_value = mock_info
        mw_ctx.__aenter__.return_value = conn
        with (
            patch('api.auth.get_conn', return_value=auth_ctx),
            patch('api.tenant_middleware.get_conn', return_value=mw_ctx),
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            resp = client.get('/api/ctx', headers={'X-Tenant-ID': 'other-clinic'})
        assert resp.status_code == 200
        assert resp.json()['slug'] == 'other-clinic'
        audit_calls = [c for c in tconn.execute.call_args_list
                       if 'INSERT INTO logs' in c.args[0]]
        assert len(audit_calls) == 1
        assert 'tenant.cross_tenant_access' in audit_calls[0].args[1]

    def test_same_tenant_does_not_touch_tenant_pool(self):
        mock_info = {'slug': 'my-clinic', 'name': 'My Clinic',
                     'db_name': 'my_clinic'}
        mock_pool = AsyncMock()
        user = User({'id': 2, 'admin': False, 'tenant': 'my-clinic'})
        client = TestClient(_make_ctx_app(user))
        mw_ctx = AsyncMock()
        conn = AsyncMock()
        conn.fetchrow.return_value = mock_info
        mw_ctx.__aenter__.return_value = conn
        with (
            patch('api.tenant_middleware.get_conn', return_value=mw_ctx),
            patch('api.tenant_middleware.TenantConnectionPool.get',
                  new=AsyncMock(return_value=mock_pool)),
        ):
            resp = client.get('/api/ctx', headers={'X-Tenant-ID': 'my-clinic'})
        assert resp.status_code == 200
        mock_pool.acquire.assert_not_called()


class TestEsTenantIndexGuard:
    """G-3: the ES indexer must never store a tenant-tagged row into the
    unscoped platform/main index (SERIAL-id collision / cross-tenant leak)."""

    async def test_index_refuses_tenant_row_without_slug(self):
        from es import es as es_mod
        fake_client = MagicMock()
        fake_client.index = AsyncMock()
        with patch.object(es_mod, 'get_client', return_value=fake_client):
            with pytest.raises(RuntimeError, match='unscoped index'):
                await es_mod.index({'id': 1, 'tenant': 'clinic_b'}, tenant_slug='')
        fake_client.index.assert_not_called()

    async def test_index_allows_tenant_row_with_slug(self):
        from es import es as es_mod
        fake_client = MagicMock()
        fake_client.index = AsyncMock()
        with patch.object(es_mod, 'get_client', return_value=fake_client):
            await es_mod.index({'id': 1, 'tenant': 'clinic_b'}, tenant_slug='clinic_b')
        fake_client.index.assert_called_once()
        _, kwargs = fake_client.index.call_args
        assert kwargs['id'] == 'clinic_b:1'
        assert kwargs['document']['tenant'] == 'clinic_b'

    async def test_index_main_store_no_slug_ok(self):
        from es import es as es_mod
        fake_client = MagicMock()
        fake_client.index = AsyncMock()
        with patch.object(es_mod, 'get_client', return_value=fake_client):
            await es_mod.index({'id': 1, 'tenant': None}, tenant_slug='')
        fake_client.index.assert_called_once()
        _, kwargs = fake_client.index.call_args
        assert kwargs['id'] == '1'
