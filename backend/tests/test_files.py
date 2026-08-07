from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.files import (
    FilesHandler, FileHandler, FileChangesHandler,
    DownloadToken, ShareFilesHandler, ShareFilesListHandler,
)
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


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
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


FILE_ROW = {
    'id': 1, 'name': 'IM000001.dcm', 'hash': 'abc123', 'size': 1024,
    'patient_id': 'PID001', 'patient_name': 'Smith^John', 'study_id': 'STU001',
    'study_description': 'Chest', 'series_number': 1, 'series_modality': 'CT',
    'indexed': True, 'deleted': False, 'meta': {},
}
FILE_EXTRA = {
    'id': 1, 'name': 'IM000001.dcm', 'hash': 'abc123',
    'patient_id': 'PID001', 'patient_name': 'Smith^John',
    'deleted': False, 'series_modality': 'CT',
}


class TestFilesHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/files', endpoint=FilesHandler)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        with patch('api.files.Files.get_paginated', new_callable=AsyncMock) as mock_get, \
             _patch_get_conn('api.files', mock_conn):
            mock_get.return_value = ([FILE_ROW], 10)
            client = TestClient(self._make_app())
            resp = client.get('/files')
        assert resp.status_code == 200
        data = resp.json()
        assert 'data' in data
        assert data['meta']['total'] == 10

    def test_list_empty(self):
        mock_conn = _mock_conn()
        with patch('api.files.Files.get_paginated', new_callable=AsyncMock) as mock_get, \
             _patch_get_conn('api.files', mock_conn):
            mock_get.return_value = ([], 0)
            client = TestClient(self._make_app())
            resp = client.get('/files')
        assert resp.status_code == 200
        assert resp.json()['meta']['total'] == 0

    def test_search(self):
        mock_conn = _mock_conn()
        with patch('api.files.es.search', new_callable=AsyncMock) as mock_search, \
             _patch_get_conn('api.files', mock_conn):
            mock_search.return_value = {'hits': {'hits': []}}
            client = TestClient(self._make_app())
            resp = client.post('/files', json={'query': {'match_all': {}}})
        assert resp.status_code == 200


class TestFileHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/files/{id}', endpoint=FileHandler)], user)

    def test_get_found(self):
        mock_conn = _mock_conn()
        with patch('api.files.get_file_by_id', new_callable=AsyncMock) as mock_get, \
             _patch_get_conn('api.files', mock_conn):
            mock_get.return_value = FILE_EXTRA
            client = TestClient(self._make_app())
            resp = client.get('/files/1')
        assert resp.status_code == 200

    def test_get_not_found(self):
        with patch('api.files.get_file_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            client = TestClient(self._make_app())
            resp = client.get('/files/999')
        assert resp.status_code == 404

    def test_update_tools_state(self):
        with patch('api.files.Files.update_tools_state', new_callable=AsyncMock), \
             patch('api.files.get_conn'):
            client = TestClient(self._make_app())
            resp = client.post('/files/1', json={'tools_state': {'window': {'center': 40, 'width': 80}}})
        assert resp.status_code == 200

    def test_update_tag(self):
        with patch('api.files.Files.update_tag', new_callable=AsyncMock), \
             patch('api.files.get_conn'):
            client = TestClient(self._make_app())
            resp = client.post('/files/1', json={'tag': {'key': 'name', 'value': 'important'}})
        assert resp.status_code == 200

    def test_update_both(self):
        with patch('api.files.Files.update_tools_state', new_callable=AsyncMock), \
             patch('api.files.Files.update_tag', new_callable=AsyncMock), \
             patch('api.files.get_conn'):
            client = TestClient(self._make_app())
            resp = client.post('/files/1', json={
                'tools_state': {'window': {'center': 40}},
                'tag': {'key': 'name', 'value': 'reviewed'},
            })
        assert resp.status_code == 200

    def test_delete(self):
        mock_conn = _mock_conn()
        with patch('api.files.Replica.master', new_callable=AsyncMock) as mock_master, \
             patch('api.files.Storage.get', new_callable=AsyncMock) as mock_storage, \
             patch('api.files.get_file_by_id', new_callable=AsyncMock) as mock_get, \
             _patch_get_conn('api.files', mock_conn):
            mock_master.return_value = {'id': 1}
            mock_storage.return_value.delete = AsyncMock()
            mock_get.return_value = FILE_EXTRA
            client = TestClient(self._make_app())
            resp = client.delete('/files/1')
        assert resp.status_code == 204

    def test_delete_no_master(self):
        mock_conn = _mock_conn()
        with patch('api.files.Replica.master', new_callable=AsyncMock) as mock_master, \
             patch('api.files.get_file_by_id', new_callable=AsyncMock) as mock_get, \
             _patch_get_conn('api.files', mock_conn):
            mock_master.return_value = None
            mock_get.return_value = FILE_EXTRA
            client = TestClient(self._make_app())
            resp = client.delete('/files/1')
        assert resp.status_code == 400

    def test_delete_missing_permission(self):
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        client = TestClient(self._make_app(user=user))
        resp = client.delete('/files/1')
        assert resp.status_code == 403


class TestFileChangesHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/files/{id}/changes', endpoint=FileChangesHandler)], user)

    def test_list_changes(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 1, 'file_id': 1, 'action': 'read', 'by_user': 1, 'created': '2026-01-01'},
        ])
        with _patch_get_conn('api.files', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/files/1/changes')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1

    def test_list_changes_empty(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.files', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/files/999/changes')
        assert resp.status_code == 200
        assert resp.json()['data'] == []


class TestDownloadToken:
    def _make_app(self, user=None):
        return _make_app([Route('/files/download_token', endpoint=DownloadToken)], user)

    def test_generate_token(self):
        with patch('api.files.gen_token') as mock_gen:
            mock_gen.return_value = 'test-token-value'
            client = TestClient(self._make_app())
            resp = client.get('/files/download_token')
        assert resp.status_code == 200
        assert resp.json()['token'] == 'test-token-value'

    def test_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/files/download_token')
        assert resp.status_code == 403


class TestShareFilesHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/files/{id}/share', endpoint=ShareFilesHandler)], user)

    def test_create_share(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.files', mock_conn), \
             patch('api.files.SharedFiles.share', new_callable=AsyncMock) as mock_share:
            mock_share.return_value = 'share-key-123'
            client = TestClient(self._make_app())
            resp = client.post('/files/1/share', json={'duration': 3600})
        assert resp.status_code == 200
        assert resp.json()['key'] == 'share-key-123'

    def test_create_share_missing_permission(self):
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        client = TestClient(self._make_app(user=user))
        resp = client.post('/files/1/share', json={'duration': 3600})
        assert resp.status_code == 403


class TestShareFilesListHandler:
    def _make_app(self, user=None):
        return _make_app([
            Route('/files/{id}/shares', endpoint=ShareFilesListHandler),
            Route('/files/{id}/shares/{share_id}', endpoint=ShareFilesListHandler),
        ], user)

    def test_list_shares(self):
        _future = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 1, 'created': datetime.now(timezone.utc),
             'expires': _future, 'hash': 'abc123def456'},
        ])
        with _patch_get_conn('api.files', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/files/1/shares')
        assert resp.status_code == 200

    def test_list_shares_empty(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.files', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/files/999/shares')
        assert resp.status_code == 200

    def test_revoke_share(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.files', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/files/1/shares/5')
        assert resp.status_code == 200

    def test_revoke_share_missing_permission(self):
        user = User({'id': 1, 'permissions': ['FILE_READ']})
        client = TestClient(self._make_app(user=user))
        resp = client.delete('/files/1/shares/5')
        assert resp.status_code == 403
