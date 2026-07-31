import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

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
        routes=[Route('/v2/metrics', endpoint=metrics_endpoint)],
        middleware=[Middleware(_MetricsTestMiddleware)],
    )


class TestMetricsEndpoint:
    def test_returns_prometheus_text_format(self):
        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('text/plain')
        body = resp.text
        assert body.startswith('# HELP') or body.startswith('# TYPE')

    def test_counter_increments_on_request(self):
        async def _ping(request):
            return PlainTextResponse('pong')

        app = Starlette(
            routes=[
                Route('/ping', endpoint=_ping),
                Route('/v2/metrics', endpoint=metrics_endpoint),
            ],
            middleware=[Middleware(_MetricsTestMiddleware)],
        )
        client = TestClient(app)

        resp1 = client.get('/v2/metrics')
        before_body = resp1.text

        for _ in range(3):
            resp = client.get('/ping')
            assert resp.status_code == 200

        resp2 = client.get('/v2/metrics')
        after_body = resp2.text

        assert 'http_requests_total{method="GET",path="/ping",status_code="200"}' in after_body

    def test_includes_db_pool_gauges(self):
        client = TestClient(_make_metrics_app())
        fake_pool = AsyncMock()
        fake_pool.get_idle_size = lambda: 5
        fake_pool.get_size = lambda: 10
        fake_pool.get_active_size = lambda: 3
        fake_db = AsyncMock()
        fake_db.pool = fake_pool
        with patch('db.conn.get_database', return_value=fake_db):
            resp = client.get('/v2/metrics')
        assert resp.status_code == 200
        assert 'db_connections_available' in resp.text
        assert 'db_connections_in_use' in resp.text

    def test_includes_db_query_duration_seconds(self):
        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert resp.status_code == 200
        assert 'db_query_duration_seconds' in resp.text

    def test_includes_redis_stream_lag_seconds(self):
        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert resp.status_code == 200
        assert 'redis_stream_lag_seconds' in resp.text

    def test_non_admin_gets_403_on_metrics(self):
        from starlette.middleware.authentication import AuthenticationMiddleware
        from api.auth import TokenAuth
        from api.telemetry import metrics_endpoint
        from api.tokens import create_token
        SECRET = 'test-secret-key-32-bytes-for-hs256!!'
        app = Starlette(
            routes=[Route('/api/v2/metrics', endpoint=metrics_endpoint)],
            middleware=[
                Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                           on_error=TokenAuth.on_auth_error),
            ],
        )
        client = TestClient(app)
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            token = create_token({'id': 2, 'admin': False}, expire={'minutes': 60})
            resp = client.get('/api/v2/metrics', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 403

    def test_admin_can_access_metrics(self):
        from starlette.middleware.authentication import AuthenticationMiddleware
        from api.auth import TokenAuth
        from api.telemetry import metrics_endpoint
        from api.tokens import create_token
        SECRET = 'test-secret-key-32-bytes-for-hs256!!'
        app = Starlette(
            routes=[Route('/api/v2/metrics', endpoint=metrics_endpoint)],
            middleware=[
                Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                           on_error=TokenAuth.on_auth_error),
            ],
        )
        client = TestClient(app)
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            token = create_token({'id': 1, 'admin': True}, expire={'minutes': 60})
            resp = client.get('/api/v2/metrics', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 200


class TestErrorLogging:
    def test_500_produces_structured_json_log(self):
        from api.telemetry import health_endpoint
        app = Starlette(
            routes=[Route('/v2/health', endpoint=health_endpoint)],
        )
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(side_effect=Exception('DB down'))
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with (
            patch('db.conn.get_conn', return_value=fake_conn),
            patch('es.es.get_client', return_value=fake_es),
        ):
            resp = client.get('/v2/health')
        assert resp.status_code == 503
        data = resp.json()
        assert 'components' in data
        assert data['components']['database']['status'] == 'error'
        assert 'DB down' in data['components']['database'].get('message', '')

    def test_500_logs_structured_json_with_error_stack(self, capsys):
        from log import setup_logging
        setup_logging()
        from app import CustomMiddleware
        async def _crash(request):
            raise RuntimeError('test explosion')

        app = Starlette(
            routes=[Route('/crash', endpoint=_crash)],
            middleware=[Middleware(CustomMiddleware)],
        )
        client = TestClient(app)
        resp = client.get('/crash')
        assert resp.status_code == 500
        out, _ = capsys.readouterr()
        assert 'test explosion' in out
        assert 'error' in out
        assert '"stack"' in out

    def test_health_down_redis_reflects_state(self):
        from api.telemetry import health_endpoint
        app = Starlette(routes=[Route('/v2/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_conn.fetch = AsyncMock(return_value=[{'id': 1, 'type': 'local', 'master': True}])
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with (
            patch('db.conn.get_conn', return_value=fake_conn),
            patch('es.es.get_client', return_value=fake_es),
            patch('api.telemetry._check_redis', return_value={'status': 'down', 'latency_ms': 0, 'message': 'connection refused'}),
            patch('api.telemetry._check_storage', return_value={'status': 'ok', 'latency_ms': 1, 'master': 'local', 'replicas': ['local']}),
            patch('api.telemetry._check_dicom_listener', return_value={'status': 'ok', 'port': 11112, 'uptime_seconds': 60, 'latency_ms': 1}),
            patch('api.telemetry._check_ingestion_service', return_value={'status': 'ok', 'stream_lag': 0}),
        ):
            resp = client.get('/v2/health')
        data = resp.json()
        assert data['status'] == 'degraded'
        assert data['components']['redis']['status'] == 'down'


_mock_probes = [
    patch('api.telemetry._check_redis', return_value={'status': 'ok', 'latency_ms': 1}),
    patch('api.telemetry._check_storage', return_value={'status': 'ok', 'latency_ms': 1, 'master': 'local', 'replicas': ['local']}),
    patch('api.telemetry._check_dicom_listener', return_value={'status': 'ok', 'port': 11112, 'uptime_seconds': 60, 'latency_ms': 1}),
    patch('api.telemetry._check_ingestion_service', return_value={'status': 'ok', 'stream_lag': 0}),
]


class TestHealthEndpoint:
    def test_returns_adr020_structure(self):
        from api.telemetry import health_endpoint
        app = Starlette(routes=[Route('/v2/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with ExitStack() as stack:
            stack.enter_context(patch('db.conn.get_conn', return_value=fake_conn))
            stack.enter_context(patch('es.es.get_client', return_value=fake_es))
            for p in _mock_probes:
                stack.enter_context(p)
            resp = client.get('/v2/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] in ('ok', 'degraded')
        assert isinstance(data['uptime_seconds'], int)
        assert data['uptime_seconds'] >= 0

    def test_health_includes_component_keys(self):
        from api.telemetry import health_endpoint
        app = Starlette(routes=[Route('/v2/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with ExitStack() as stack:
            stack.enter_context(patch('db.conn.get_conn', return_value=fake_conn))
            stack.enter_context(patch('es.es.get_client', return_value=fake_es))
            for p in _mock_probes:
                stack.enter_context(p)
            resp = client.get('/v2/health')
        data = resp.json()
        components = data.get('components', {})
        for key in ('database', 'elasticsearch'):
            assert key in components
            assert 'status' in components[key]
            assert 'latency_ms' in components[key]
            assert isinstance(components[key]['latency_ms'], int)

    def test_health_includes_all_component_keys(self):
        from api.telemetry import health_endpoint
        app = Starlette(routes=[Route('/v2/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_conn.fetch = AsyncMock(return_value=[{'id': 1, 'type': 'local', 'master': True}])
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        with ExitStack() as stack:
            stack.enter_context(patch('db.conn.get_conn', return_value=fake_conn))
            stack.enter_context(patch('es.es.get_client', return_value=fake_es))
            for p in _mock_probes:
                stack.enter_context(p)
            resp = client.get('/v2/health')
        data = resp.json()
        components = data.get('components', {})
        for key in ('database', 'elasticsearch', 'redis', 'storage', 'dicom_listener', 'ingestion_service'):
            assert key in components, f'{key} missing from health response'

    def test_health_includes_ingestion_service(self):
        from api.telemetry import health_endpoint
        app = Starlette(routes=[Route('/v2/health', endpoint=health_endpoint)])
        client = TestClient(app)
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_conn.fetch = AsyncMock(return_value=[{'id': 1, 'type': 'local', 'master': True}])
        fake_es = AsyncMock()
        fake_es.ping = AsyncMock(return_value=True)
        fake_monitor = MagicMock()
        fake_monitor.metrics = MagicMock(return_value={
            'events:ingestion': {'group': 'ingestion-service', 'length': 10, 'pending': 0},
        })
        with ExitStack() as stack:
            stack.enter_context(patch('db.conn.get_conn', return_value=fake_conn))
            stack.enter_context(patch('es.es.get_client', return_value=fake_es))
            for p in _mock_probes:
                stack.enter_context(p)
            resp = client.get('/v2/health')
        data = resp.json()
        components = data.get('components', {})
        assert 'ingestion_service' in components
        assert 'status' in components['ingestion_service']
        assert 'stream_lag' in components['ingestion_service']
        assert isinstance(components['ingestion_service']['stream_lag'], int)


class TestCStoreMetrics:
    def test_dicom_cstore_throughput_defined_in_metrics(self):
        from api.telemetry import dicom_cstore_throughput_bytes

        dicom_cstore_throughput_bytes.inc(1024)

        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert 'dicom_cstore_throughput_bytes' in resp.text
        lines = resp.text.split('\n')
        matching = [l for l in lines if l and not l.startswith('#') and 'dicom_cstore_throughput_bytes_total' in l]
        assert len(matching) == 1, f'Expected 1 metric data line, got: {matching}'
        val = float(matching[0].split()[-1])
        assert val >= 1024.0, f'Expected value >= 1024.0, got {val}'



class TestDicomWebMetrics:
    def test_dicomweb_requests_total_defined_in_metrics(self):
        from api.telemetry import dicomweb_requests_total

        dicomweb_requests_total.labels(method='GET', resource='studies').inc()

        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert 'dicomweb_requests_total' in resp.text
        assert 'studies' in resp.text


class TestInProgressGauge:
    def test_http_requests_in_progress_defined_in_metrics(self):
        client = TestClient(_make_metrics_app())
        resp = client.get('/v2/metrics')
        assert 'http_requests_in_progress' in resp.text
