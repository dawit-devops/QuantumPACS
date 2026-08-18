import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

import api.admin as admin_module
from api.auth import User
from api.admin import (
    AdminStatusHandler, AdminMaintenanceHandler, AdminConfigHandler,
    AdminBackupsHandler, AdminBackupHandler, AdminBackupRestoreHandler,
)
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({
            'id': 1, 'admin': True, 'permissions': ['SYSTEM_ADMIN'], 'role': 'super_admin',
        })

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(module, mock_conn):
    return patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture(autouse=True)
def _reset_maintenance_state():
    admin_module._maintenance.update(
        {'active': False, 'reason': '', 'since': None},
    )
    yield
    admin_module._maintenance.update(
        {'active': False, 'reason': '', 'since': None},
    )


class TestMaintenanceState:
    def test_gate_helpers(self):
        admin_module._maintenance.update(
            {'active': True, 'reason': 'upgrade', 'since': 'x'},
        )
        assert admin_module.maintenance_active() is True
        assert admin_module.maintenance_exempt('/api/login')
        assert admin_module.maintenance_exempt('/api/v2/admin/maintenance')
        assert not admin_module.maintenance_exempt('/api/files/upload')
        assert not admin_module.maintenance_exempt('/api/dicomweb/studies')

    def test_status_public_shape(self):
        admin_module._maintenance.update(
            {'active': True, 'reason': 'upgrade', 'since': '2026-08-14T00:00:00+00:00'},
        )
        client = TestClient(_make_app([
            Route('/admin/status', endpoint=AdminStatusHandler),
        ]))
        resp = client.get('/admin/status')
        assert resp.status_code == 200
        m = resp.json()['maintenance']
        assert m['active'] is True
        assert m['reason'] == 'upgrade'

    def test_maintenance_on_requires_reason(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.admin', mock_conn):
            client = TestClient(_make_app([
                Route('/admin/maintenance', endpoint=AdminMaintenanceHandler, methods=['POST']),
            ]))
            resp = client.post('/admin/maintenance', json={'active': True, 'reason': '  '})
        assert resp.status_code == 422
        assert admin_module.maintenance_active() is False

    def test_maintenance_toggle_persists_and_audits(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.admin', mock_conn):
            client = TestClient(_make_app([
                Route('/admin/maintenance', endpoint=AdminMaintenanceHandler, methods=['POST']),
                Route('/admin/status', endpoint=AdminStatusHandler),
            ]))
            resp = client.post('/admin/maintenance', json={'active': True, 'reason': 'v3 release'})
            assert resp.status_code == 200
            assert resp.json()['maintenance']['active'] is True
            assert admin_module.maintenance_active() is True
            # persisted to platform_state + audit written
            assert mock_conn.execute.await_count >= 2
            # turn it off
            resp = client.post('/admin/maintenance', json={'active': False, 'reason': ''})
            assert resp.status_code == 200
            assert admin_module.maintenance_active() is False

    def test_maintenance_endpoint_requires_system_admin(self):
        user = User({'id': 1, 'permissions': ['USER_READ'], 'role': 'tenant_admin'})
        client = TestClient(_make_app([
            Route('/admin/maintenance', endpoint=AdminMaintenanceHandler, methods=['POST']),
        ], user=user))
        resp = client.post('/admin/maintenance', json={'active': True, 'reason': 'x'})
        assert resp.status_code == 403


class TestAdminConfig:
    def _config_route(self, user=None):
        return _make_app([Route('/admin/config', endpoint=AdminConfigHandler)], user=user)

    def test_get_returns_whitelist(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.admin', mock_conn):
            client = TestClient(self._config_route())
            resp = client.get('/admin/config')
        assert resp.status_code == 200
        settings = resp.json()['settings']
        assert 'max_upload_size_mb' in settings
        assert 'token_expiry_days' in settings
        assert settings['token_expiry_days']['restart'] is False

    def test_put_updates_live_key_and_audits(self):
        mock_conn = _mock_conn()
        old = admin_module.config.get('max_upload_size_mb')
        try:
            with _patch_get_conn('api.admin', mock_conn):
                client = TestClient(self._config_route())
                resp = client.put('/admin/config', json={
                    'settings': {'max_upload_size_mb': {'value': 999}},
                })
            assert resp.status_code == 200
            assert 'max_upload_size_mb' in resp.json()['updated']
            assert admin_module.config['max_upload_size_mb'] == 999
            assert mock_conn.execute.await_count >= 2  # setting + audit
        finally:
            admin_module.config['max_upload_size_mb'] = old

    def test_put_rejects_unknown_key(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.admin', mock_conn):
            client = TestClient(self._config_route())
            resp = client.put('/admin/config', json={
                'settings': {'db_password': {'value': 'hax'}},
            })
        assert resp.status_code == 422
        assert mock_conn.execute.await_count == 0


class TestAdminBackups:
    def _backup_row(self, bid):
        return {
            'id': bid, 'status': 'completed', 'kind': 'metadata',
            'artifact_key': f'backup/{bid}.json', 'size_bytes': 12,
            'files_count': 3, 'bytes_count': 99, 'created_by': 1,
            'created_at': '2026-08-14T00:00:00Z',
        }

    def test_create_backup_writes_artifact_and_audits(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])  # no files in manifest
        fake_replica = {'id': 1, 'type': 'local', 'location': '/tmp/x', 'meta': None}
        # master() is called in _gather_manifest AND in post(); Backups.get() last.
        mock_conn.fetchrow = AsyncMock(side_effect=[
            fake_replica, fake_replica, self._backup_row('b1'),
        ])
        fake_storage = MagicMock()
        fake_storage.copy = AsyncMock(return_value={'location': '/tmp/x'})
        with patch('api.admin.Storage.get', new=AsyncMock(return_value=fake_storage)):
            with _patch_get_conn('api.admin', mock_conn):
                client = TestClient(_make_app([
                    Route('/admin/backups', endpoint=AdminBackupsHandler),
                ]))
                resp = client.post('/admin/backups')
        assert resp.status_code == 200
        assert resp.json()['data']['status'] == 'completed'
        assert fake_storage.copy.await_count == 1
        assert mock_conn.execute.await_count >= 2  # row update + audit

    def test_create_backup_marks_failed_on_error(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(side_effect=RuntimeError('boom'))
        with _patch_get_conn('api.admin', mock_conn):
            client = TestClient(_make_app([
                Route('/admin/backups', endpoint=AdminBackupsHandler),
            ]))
            resp = client.post('/admin/backups')
        assert resp.status_code == 500

    def test_download_returns_artifact(self):
        mock_conn = _mock_conn()
        bid = 'b1'
        fake_replica = {'id': 1, 'type': 'local', 'location': '/tmp/x', 'meta': None}
        # Backups.get() first, then Replica.master()
        mock_conn.fetchrow = AsyncMock(side_effect=[
            self._backup_row(bid), fake_replica,
        ])
        fake_storage = MagicMock()
        fake_storage.fetch = AsyncMock(return_value=b'{"kind": "metadata"}')
        with patch('api.admin.Storage.get', new=AsyncMock(return_value=fake_storage)):
            with _patch_get_conn('api.admin', mock_conn):
                client = TestClient(_make_app([
                    Route('/admin/backups/{id}', endpoint=AdminBackupHandler),
                ]))
                resp = client.get(f'/admin/backups/{bid}')
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('application/json')
        assert json.loads(resp.content) == {'kind': 'metadata'}

    def test_restore_verifies_artifact(self):
        mock_conn = _mock_conn()
        bid = 'b1'
        fake_replica = {'id': 1, 'type': 'local', 'location': '/tmp/x', 'meta': None}
        # Backups.get() first, then Replica.master()
        mock_conn.fetchrow = AsyncMock(side_effect=[
            self._backup_row(bid), fake_replica,
        ])
        fake_storage = MagicMock()
        fake_storage.fetch = AsyncMock(return_value=json.dumps({
            'kind': 'metadata', 'generated_at': 'x',
            'counts': {'files': 3, 'bytes': 99},
            'master_replica': 1,
        }).encode('utf-8'))
        with patch('api.admin.Storage.get', new=AsyncMock(return_value=fake_storage)):
            with _patch_get_conn('api.admin', mock_conn):
                client = TestClient(_make_app([
                    Route('/admin/backups/{id}/restore', endpoint=AdminBackupRestoreHandler, methods=['POST']),
                ]))
                resp = client.post(f'/admin/backups/{bid}/restore')
        assert resp.status_code == 200
        v = resp.json()['verification']
        assert v['valid'] is True
        assert v['files'] == 3

    def test_backup_endpoints_require_system_admin(self):
        user = User({'id': 1, 'permissions': ['USER_READ'], 'role': 'tenant_admin'})
        client = TestClient(_make_app([
            Route('/admin/backups', endpoint=AdminBackupsHandler),
        ], user=user))
        resp = client.get('/admin/backups')
        assert resp.status_code == 403
