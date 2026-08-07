from contextlib import ExitStack
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
    from api.dashboard_metrics import DashboardHealthHandler
    return Starlette(
        routes=[
            Route('/v2/dashboard/health', endpoint=DashboardHealthHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


COMPONENTS = ('database', 'elasticsearch', 'redis', 'storage', 'dicom_listener',
              'ingestion_service', 'hl7', 'fhir', 'auth')


def _mock_all_checks(**overrides):
    defaults = {name: {'status': 'ok', 'latency_ms': 1} for name in COMPONENTS}
    defaults.update(overrides)
    check_names = {'database': 'db', 'elasticsearch': 'es', 'hl7': 'hl7_listener'}
    return [
        patch(f'api.telemetry._check_{check_names.get(name, name)}', new=AsyncMock(return_value=result))
        for name, result in defaults.items()
    ]


class TestDashboardHealth:
    def test_requires_metrics_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/v2/dashboard/health')
        assert resp.status_code == 403

    def test_returns_health_with_all_component_keys(self):
        user = User({'id': 1, 'permissions': ['METRICS_READ']})
        client = TestClient(_make_app(user))
        with ExitStack() as stack:
            for p in _mock_all_checks():
                stack.enter_context(p)
            resp = client.get('/v2/dashboard/health')
        assert resp.status_code == 200
        body = resp.json()
        assert body['status'] == 'ok'
        assert isinstance(body['uptime_seconds'], int)
        assert body['uptime_seconds'] >= 0
        assert set(body['components'].keys()) == set(COMPONENTS)
        for key in COMPONENTS:
            assert 'status' in body['components'][key]
            assert 'latency_ms' in body['components'][key]
            assert isinstance(body['components'][key]['latency_ms'], int)

    def test_degraded_component_flips_overall_status(self):
        user = User({'id': 1, 'permissions': ['METRICS_READ']})
        client = TestClient(_make_app(user))
        with ExitStack() as stack:
            for p in _mock_all_checks(hl7={'status': 'degraded', 'port': 12579, 'latency_ms': 0, 'message': 'HL7 MLLP listener not reachable'}):
                stack.enter_context(p)
            resp = client.get('/v2/dashboard/health')
        assert resp.status_code == 200
        body = resp.json()
        assert body['status'] == 'degraded'
        assert body['components']['hl7']['status'] == 'degraded'
        assert 'message' in body['components']['hl7']

    def test_db_error_returns_503_with_body(self):
        user = User({'id': 1, 'permissions': ['METRICS_READ']})
        client = TestClient(_make_app(user))
        with ExitStack() as stack:
            for p in _mock_all_checks(database={'status': 'error', 'latency_ms': 5, 'message': 'connection refused'}):
                stack.enter_context(p)
            resp = client.get('/v2/dashboard/health')
        assert resp.status_code == 503
        body = resp.json()
        assert body['status'] == 'degraded'
        assert body['components']['database']['status'] == 'error'
        assert 'connection refused' in body['components']['database']['message']
