"""M-4: ris_mpps_events must have a read path — the modality audit trail
is currently write-only (S6-08 finding)."""
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
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
    from api.mpps_events import MppsEventsHandler
    return Starlette(
        routes=[Route('/mpps/events', endpoint=MppsEventsHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestMppsEventsReadPath:
    def test_requires_worklist_read(self):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.get('/mpps/events?accession=ACC1')
        assert resp.status_code == 403

    def test_requires_accession_param(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        resp = client.get('/mpps/events')
        assert resp.status_code == 400

    def test_returns_events_for_accession(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'accession_number': 'ACC1', 'event_type': 'N_CREATE',
             'mpps_status': 'IN_PROGRESS'},
            {'accession_number': 'ACC1', 'event_type': 'N_SET',
             'mpps_status': 'COMPLETED'},
        ]
        with patch('api.mpps_events.get_conn', return_value=mock_conn):
            resp = client.get('/mpps/events?accession=ACC1')
        assert resp.status_code == 200
        body = resp.json()
        assert len(body['data']) == 2
        assert body['data'][0]['event_type'] == 'N_CREATE'
        assert body['total'] == 2

    def test_rejects_oversized_limit(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        with patch('api.mpps_events.get_conn', return_value=mock_conn):
            resp = client.get('/mpps/events?accession=ACC1&limit=99999')
        assert resp.status_code == 400
