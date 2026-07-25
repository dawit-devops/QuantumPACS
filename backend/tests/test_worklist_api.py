from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.worklist import WorklistHandler, WorklistEntryHandler
    return Starlette(
        routes=[
            Route('/worklist', endpoint=WorklistHandler),
            Route('/worklist/{id}', endpoint=WorklistEntryHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestWorklistCreate:
    def test_create_requires_worklist_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/worklist', json={'patient_id': 'P001'})
        assert resp.status_code == 403

    def test_create_returns_400_without_patient_id(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_app(user))
        resp = client.post('/worklist', json={})
        assert resp.status_code == 422

    def test_create_success(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl.create.return_value = {'id': 'entry-uuid'}
            mock_wl_cls.return_value = mock_wl
            with patch('api.worklist.get_conn'):
                resp = client.post('/worklist', json={
                    'patient_id': 'P001',
                    'patient_name': 'Test^Patient',
                    'accession_number': 'ACC001',
                    'modality': 'CT',
                })
        assert resp.status_code == 201
        data = resp.json()
        assert data['data']['id'] == 'entry-uuid'


class TestWorklistList:
    def test_list_requires_worklist_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/worklist')
        assert resp.status_code == 403

    def test_list_returns_entries(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl.search.return_value = [{'id': '1', 'patient_id': 'P001'}]
            mock_wl_cls.return_value = mock_wl
            with patch('api.worklist.get_conn'):
                resp = client.get('/worklist')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 1

    def test_list_filters_by_status(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl.search.return_value = []
            mock_wl_cls.return_value = mock_wl
            with patch('api.worklist.get_conn'):
                client.get('/worklist?status=scheduled')
                _, kwargs = mock_wl.search.call_args
                assert kwargs.get('status') == 'scheduled'

    def test_list_filters_by_modality(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl.search.return_value = []
            mock_wl_cls.return_value = mock_wl
            with patch('api.worklist.get_conn'):
                client.get('/worklist?modality=CT')
                _, kwargs = mock_wl.search.call_args
                assert kwargs.get('modality') == 'CT'


class TestWorklistUpdate:
    def test_update_requires_worklist_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.put('/worklist/entry-id', json={'modality': 'MR'})
        assert resp.status_code == 403

    def test_update_success(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl.get_by_accession.return_value = None
            mock_wl_cls.return_value = mock_wl
            mock_conn = AsyncMock()
            with patch('api.worklist.get_conn', return_value=mock_conn):
                resp = client.put('/worklist/entry-id', json={'modality': 'MR'})
        assert resp.status_code == 200


class TestWorklistCancel:
    def test_cancel_requires_worklist_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.delete('/worklist/entry-id')
        assert resp.status_code == 403

    def test_cancel_success(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_app(user))
        with patch('api.worklist.Worklist') as mock_wl_cls:
            mock_wl = AsyncMock()
            mock_wl_cls.return_value = mock_wl
            with patch('api.worklist.get_conn'):
                resp = client.delete('/worklist/entry-id')
        assert resp.status_code == 200
