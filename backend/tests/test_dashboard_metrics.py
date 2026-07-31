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
    from api.dashboard_metrics import DashboardMetricsHandler
    return Starlette(
        routes=[
            Route('/v2/dashboard/metrics', endpoint=DashboardMetricsHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestDashboardMetrics:
    def test_requires_metrics_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/v2/dashboard/metrics')
        assert resp.status_code == 403

    def test_returns_metrics(self):
        user = User({'id': 1, 'permissions': ['METRICS_READ']})
        client = TestClient(_make_app(user))

        fake_conn = AsyncMock()
        fake_conn.fetchval = AsyncMock(side_effect=[10, 20, 30, 40, 5, 1000000])
        fake_conn.fetch = AsyncMock(side_effect=[
            [{'modality': 'CT', 'count': 15}, {'modality': 'MR', 'count': 10}],
            [{'day': '2026-07-20', 'count': 5}, {'day': '2026-07-21', 'count': 3}],
            [{'id': 40, 'name': 'latest.dcm', 'created': '2026-07-26 12:00:00'}],
        ])

        fake_ctx = AsyncMock()
        fake_ctx.__aenter__.return_value = fake_conn
        fake_ctx.__aexit__.return_value = None

        with patch('api.dashboard_metrics.get_conn', return_value=fake_ctx):
            resp = client.get('/v2/dashboard/metrics')

        assert resp.status_code == 200
        body = resp.json()
        assert 'totals' in body
        assert body['totals']['patients'] == 10
        assert body['totals']['files'] == 40
        assert body['totals']['storage_bytes'] == 1000000
        assert body['modalities'] == {'CT': 15, 'MR': 10}
        assert len(body['ingestion_30d']) == 2
        assert len(body['latest_files']) == 1
