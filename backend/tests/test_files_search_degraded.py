"""P2-5 (tenant_admin review): when the search backend is down, the Files
search response must carry search_available=False so the UI renders a
degraded notice instead of a misleading 'No files uploaded' empty state."""

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.files import FilesHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['FILE_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app():
    return Starlette(
        routes=[Route('/files', FilesHandler, methods=['GET', 'POST'])],
        middleware=[Middleware(_FakeAuth)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def test_search_marks_unavailable_when_es_down():
    """es.available() False -> response carries search_available=False."""
    with (
        patch('api.files.es.search', new=AsyncMock(return_value={'data': [], 'total': 0})),
        patch('api.files.es.available', return_value=False),
    ):
        client = TestClient(_make_app())
        resp = client.post('/files', json={'query': 'x', 'results': 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body['search_available'] is False
    assert body['data'] == []


def test_search_omits_flag_when_es_up():
    """es.available() True -> the response keeps its normal shape (no flag),
    so the frontend's truthy default stays 'search is available'."""
    with (
        patch('api.files.es.search', new=AsyncMock(return_value={'data': [{'id': 1}], 'total': 1})),
        patch('api.files.es.available', return_value=True),
    ):
        client = TestClient(_make_app())
        resp = client.post('/files', json={'query': '', 'results': 10})
    assert resp.status_code == 200
    body = resp.json()
    assert 'search_available' not in body
    assert body['total'] == 1
