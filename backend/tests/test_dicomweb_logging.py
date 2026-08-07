"""Tests for the DICOMweb request-logging middleware (api/dicomweb_logging.py)."""
import json

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from api.auth import User
from api.dicomweb_logging import DicomWebLogMiddleware, classify_request


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None, reject=False):
        super().__init__(app)
        self._user = user or User({'id': 7, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE'], 'tenant': 'acme'})
        self._reject = reject

    async def dispatch(self, request, call_next):
        if self._reject:
            return JSONResponse({'error': 'Invalid auth'}, status_code=401)
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


async def _ok(request):
    return Response(status_code=200)


async def _created(request):
    return Response(status_code=201)


def _make_app(reject=False):
    return Starlette(
        routes=[
            Route('/api/dicomweb/studies', endpoint=_ok),
            Route('/api/dicomweb/studies/{uid}', endpoint=_ok),
            Route('/api/dicomweb/studies/{uid}/instances/{iid}/frames/{fid}', endpoint=_ok),
            Route('/api/dicomweb/studies/{uid}/archive', endpoint=_ok),
            Route('/api/wado', endpoint=_ok),
            Route('/api/dicomweb/admin/metrics', endpoint=_ok),
            Route('/api/other', endpoint=_ok),
            Route('/api/dicomweb/studies', endpoint=_created, methods=['POST']),
        ],
        middleware=[
            # Logger sits OUTSIDE auth, exactly like the real app (app.py):
            # rejected requests still pass through it and are recorded.
            Middleware(DicomWebLogMiddleware),
            Middleware(_FakeAuth, reject=reject),
        ],
    )


def _mock_conn():
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def captured_conn():
    conn = _mock_conn()
    with patch(
        'api.dicomweb_logging.get_conn',
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ),
    ):
        yield conn


def _last_log_payload(conn):
    assert conn.execute.await_count == 1, 'expected exactly one log INSERT'
    return conn.execute.await_args.args[1]


class TestClassifyRequest:
    @pytest.mark.parametrize('method,path,expected', [
        ('POST', '/api/dicomweb/studies', 'stow'),
        ('POST', '/api/dicomweb/studies/1.2.3/instances', 'stow'),
        ('GET', '/api/dicomweb/studies', 'qido'),
        ('GET', '/api/dicomweb/studies/1.2.3/series', 'qido'),
        ('GET', '/api/dicomweb/studies/1.2.3/series/4.5/instances', 'qido'),
        ('GET', '/api/dicomweb/studies/1.2.3', 'wado'),
        ('GET', '/api/dicomweb/studies/1.2.3/series/4.5/instances/6.7', 'wado'),
        ('GET', '/api/dicomweb/studies/1.2.3/instances/6.7/frames/2', 'frames'),
        ('GET', '/api/dicomweb/studies/1.2.3/archive', 'archive'),
        ('GET', '/api/wado', 'wado_uri'),
        ('GET', '/api/v2/dicomweb/studies', 'qido'),
        ('GET', '/api/dicomweb/studies/1.2.3/series/4.5/instances/6.7/thumbnail', 'wado'),
    ])
    def test_kinds(self, method, path, expected):
        assert classify_request(method, path) == expected


class TestDicomWebLogMiddleware:
    def test_logs_qido_request(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/dicomweb/studies')
        assert resp.status_code == 200
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['event'] == 'dicomweb.request'
        assert payload['actor'] == 7
        assert payload['tenant'] == 'acme'
        assert payload['resource'] == {'type': 'dicomweb', 'id': 'qido'}
        assert payload['detail']['method'] == 'GET'
        assert payload['detail']['status'] == 200
        assert payload['detail']['kind'] == 'qido'
        assert payload['detail']['duration_ms'] >= 0

    def test_logs_stow_request(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.post('/api/dicomweb/studies')
        assert resp.status_code == 201
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['detail']['kind'] == 'stow'
        assert payload['detail']['status'] == 201

    def test_logs_frames_request(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/dicomweb/studies/1.2.3/instances/6.7/frames/2')
        assert resp.status_code == 200
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['detail']['kind'] == 'frames'

    def test_logs_archive_request(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/dicomweb/studies/1.2.3/archive')
        assert resp.status_code == 200
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['detail']['kind'] == 'archive'

    def test_logs_wado_uri_request(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/wado?requestType=WADO')
        assert resp.status_code == 200
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['detail']['kind'] == 'wado_uri'

    def test_logs_rejected_request_without_actor(self, captured_conn):
        client = TestClient(_make_app(reject=True))
        resp = client.get('/api/dicomweb/studies')
        assert resp.status_code == 401
        payload = json.loads(_last_log_payload(captured_conn))
        assert payload['actor'] is None
        assert payload['detail']['status'] == 401

    def test_skips_admin_metrics(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/dicomweb/admin/metrics')
        assert resp.status_code == 200
        assert captured_conn.execute.await_count == 0

    def test_skips_non_dicomweb_paths(self, captured_conn):
        client = TestClient(_make_app())
        resp = client.get('/api/other')
        assert resp.status_code == 200
        assert captured_conn.execute.await_count == 0

    def test_skips_options_preflight(self, captured_conn):
        client = TestClient(_make_app())
        # No CORSMiddleware in this app, so OPTIONS yields 405 — the point is
        # the preflight must not be recorded as DICOMweb service traffic.
        resp = client.options('/api/dicomweb/studies')
        assert resp.status_code == 405
        assert captured_conn.execute.await_count == 0

    def test_log_write_failure_does_not_break_response(self):
        conn = _mock_conn()
        conn.execute = AsyncMock(side_effect=RuntimeError('db down'))
        with patch(
            'api.dicomweb_logging.get_conn',
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=conn),
                __aexit__=AsyncMock(return_value=None),
            ),
        ):
            client = TestClient(_make_app())
            resp = client.get('/api/dicomweb/studies')
        assert resp.status_code == 200
