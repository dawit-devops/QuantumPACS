import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.responses import PlainTextResponse

from api.telemetry import metrics_endpoint, record_request


class _MetricsTestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        import time
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        record_request(request.method, request.url.path, response.status_code, elapsed)
        return response


def _make_metrics_app():
    return Starlette(
        routes=[Route('/metrics', endpoint=metrics_endpoint)],
        middleware=[Middleware(_MetricsTestMiddleware)],
    )


class TestMetricsEndpoint:
    def test_returns_prometheus_text_format(self):
        client = TestClient(_make_metrics_app())
        resp = client.get('/metrics')
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('text/plain; version=0.0.4')
        body = resp.text
        assert body.startswith('# HELP') or body.startswith('# TYPE')

    def test_counter_increments_on_request(self):
        async def _ping(request):
            return PlainTextResponse('pong')

        app = Starlette(
            routes=[
                Route('/ping', endpoint=_ping),
                Route('/metrics', endpoint=metrics_endpoint),
            ],
            middleware=[Middleware(_MetricsTestMiddleware)],
        )
        client = TestClient(app)

        resp1 = client.get('/metrics')
        before_body = resp1.text

        for _ in range(3):
            resp = client.get('/ping')
            assert resp.status_code == 200

        resp2 = client.get('/metrics')
        after_body = resp2.text

        assert 'http_requests_total{method="GET",path="/ping",status_code="200"}' in after_body


class TestHealthEndpoint:
    def test_returns_adr020_structure(self):
        from api.telemetry import health_endpoint
        from unittest.mock import patch, AsyncMock
        app = Starlette(routes=[Route('/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with (
            patch('db.conn.get_conn', return_value=fake_conn),
            patch('es.es.get_client', return_value=fake_es),
        ):
            resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] in ('ok', 'degraded')
        assert isinstance(data['uptime_seconds'], int)
        assert data['uptime_seconds'] >= 0

    def test_health_includes_component_keys(self):
        from api.telemetry import health_endpoint
        from unittest.mock import patch, AsyncMock
        app = Starlette(routes=[Route('/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with (
            patch('db.conn.get_conn', return_value=fake_conn),
            patch('es.es.get_client', return_value=fake_es),
        ):
            resp = client.get('/health')
        data = resp.json()
        components = data.get('components', {})
        for key in ('database', 'elasticsearch'):
            assert key in components
            assert 'status' in components[key]
            assert 'latency_ms' in components[key]
            assert isinstance(components[key]['latency_ms'], int)
