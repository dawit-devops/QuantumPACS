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


class _AdminUserMiddleware:
    """Pure ASGI middleware granting an admin scope['user'].

    BaseHTTPMiddleware is unusable here: starlette 1.x does not propagate its
    scope mutations to the endpoint, and the metrics admin gate (M-1) would
    reject every request as anonymous.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from api.auth import User
        if scope['type'] == 'http':
            scope['user'] = User({'id': 1, 'admin': True, 'permissions': []})
        await self.app(scope, receive, send)


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
        middleware=[Middleware(_MetricsTestMiddleware), Middleware(_AdminUserMiddleware)],
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
            middleware=[Middleware(_MetricsTestMiddleware), Middleware(_AdminUserMiddleware)],
        )
        client = TestClient(app)

        client.get('/v2/metrics')

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
        fake_pool.get_size = lambda: 8
        fake_db = AsyncMock()
        # Database stores the (traced) pool as `_pool`; the wrapper forwards
        # get_idle_size/get_size to the underlying asyncpg pool.
        fake_db._pool = fake_pool
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

    def test_non_admin_metrics_denial_has_envelope_message(self):
        """The metrics admin gate must emit a proper forbidden() envelope —
        a bare HTTPException(403) with empty detail would render as an empty
        error string through the app-level http_exception handler."""
        from starlette.exceptions import HTTPException
        from starlette.middleware.authentication import AuthenticationMiddleware
        from api.auth import TokenAuth
        from api.telemetry import metrics_endpoint
        from api.tokens import create_token

        async def _http_exception(request, exc):
            from api.response import server_error, apply_cors_headers
            detail = getattr(exc, 'detail', None) or 'Request failed'
            return apply_cors_headers(request, server_error(str(detail), status_code=exc.status_code))

        SECRET = 'test-secret-key-32-bytes-for-hs256!!'
        app = Starlette(
            routes=[Route('/api/metrics', endpoint=metrics_endpoint)],
            middleware=[
                Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                           on_error=TokenAuth.on_auth_error),
            ],
            exception_handlers={HTTPException: _http_exception},
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
            token = create_token({'id': 3, 'admin': False}, expire={'minutes': 60})
            resp = client.get('/api/metrics', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 403
        assert resp.json() == {'error': {'code': 'FORBIDDEN', 'message': 'Admin access required'}}

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
        # The DB probe must never leak the raw asyncpg exception (which can
        # embed connection internals) — only the stable failure class.
        assert data['components']['database']['message'] == 'Database unreachable'
        assert 'DB down' not in data['components']['database']['message']

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
        matching = [line for line in lines if line and not line.startswith('#') and 'dicom_cstore_throughput_bytes_total' in line]
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


@pytest.mark.asyncio
class TestHealthProbeSanitization:
    """M-4: failed probes must emit stable generic messages — raw exception
    strings can embed hosts/ports/credentials — and success payloads must not
    expose ports or storage backend types."""

    async def test_es_probe_sanitizes_exception(self):
        from api.telemetry import _check_es
        with patch('es.es.get_client', side_effect=RuntimeError('es://admin:pw@internal-es:9200 down')):
            result = await _check_es()
        assert result['status'] == 'error'
        assert result['message'] == 'Elasticsearch unreachable'
        assert 'internal-es' not in str(result)
        assert '9200' not in str(result)

    async def test_redis_probe_sanitizes_exception(self):
        from api.telemetry import _check_redis
        with patch('api.redis_client.is_available', return_value=True):
            with patch('api.redis_client.get_client', side_effect=ConnectionError('redis 10.0.0.5:6379 refused')):
                result = await _check_redis()
        assert result['status'] == 'error'
        assert result['message'] == 'Redis unreachable'
        assert '10.0.0.5' not in str(result)

    async def test_storage_probe_sanitizes_exception(self):
        from api.telemetry import _check_storage
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetch = AsyncMock(side_effect=Exception('postgres://user:pw@db:5432 broken'))
        with patch('db.conn.get_conn', return_value=fake_conn):
            result = await _check_storage()
        assert result['status'] == 'error'
        assert result['message'] == 'Storage backend unreachable'
        assert '5432' not in str(result)

    async def test_storage_probe_does_not_leak_backend_types(self):
        from api.telemetry import _check_storage
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetch = AsyncMock(return_value=[
            {'id': 1, 'type': 'local', 'master': True},
            {'id': 2, 'type': 's3', 'master': False},
        ])
        with patch('db.conn.get_conn', return_value=fake_conn):
            result = await _check_storage()
        assert result['status'] == 'ok'
        assert 'master' not in result
        assert 'replicas' not in result
        assert 's3' not in str(result)

    async def test_dicom_listener_probe_does_not_leak_port(self):
        from api.telemetry import _check_dicom_listener
        with patch('config.config', {'dicom_cstore_port': '11112'}):
            with patch('socket.create_connection', side_effect=OSError('refused')):
                result = await _check_dicom_listener()
        assert result['status'] == 'degraded'
        assert result['message'] == 'DICOM listener not reachable'
        assert 'port' not in result
        assert '11112' not in str(result)

    async def test_hl7_listener_probe_does_not_leak_port(self):
        from api.telemetry import _check_hl7_listener
        with patch('config.config', {'hl7_mllp_port': '12579'}):
            with patch('socket.create_connection', side_effect=OSError('refused')):
                result = await _check_hl7_listener()
        assert result['status'] == 'degraded'
        assert result['message'] == 'HL7 MLLP listener not reachable'
        assert 'port' not in result
        assert '12579' not in str(result)

    async def test_ingestion_probe_sanitizes_exception(self):
        from api.telemetry import _check_ingestion_service
        bad_monitor = MagicMock()
        bad_monitor.metrics = MagicMock(side_effect=RuntimeError('consumer lag exploded'))
        with patch('api.telemetry.get_stream_monitor', return_value=bad_monitor):
            result = await _check_ingestion_service()
        assert result['status'] == 'error'
        assert result['message'] == 'Ingestion service unreachable'
        assert 'exploded' not in str(result)

    async def test_fhir_probe_sanitizes_exception(self):
        from api.telemetry import _check_fhir
        fake_conn = AsyncMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=None)
        fake_conn.fetch = AsyncMock(side_effect=Exception('fhir db credentials expired'))
        with patch('db.conn.get_conn', return_value=fake_conn):
            result = await _check_fhir()
        assert result['status'] == 'error'
        assert result['message'] == 'FHIR configuration unreachable'
        assert 'credentials' not in str(result)

    async def test_token_blocklist_probe_sanitizes_exception(self):
        from api.telemetry import _check_token_blocklist
        bad_client = AsyncMock()
        bad_client.ping = AsyncMock(side_effect=ConnectionError('redis 10.1.2.3:6379 down'))
        with patch('api.redis_client.is_available', return_value=True):
            with patch('api.redis_client.get_client', return_value=bad_client):
                result = await _check_token_blocklist()
        assert result['status'] == 'degraded'
        assert result['message'] == 'Token blocklist fail-open active (redis unreachable)'
        assert '10.1.2.3' not in str(result)


class TestRisReportTatMetric:
    """S12-33: ris_report_tat_seconds histogram exists and the sign handler
    observes it labelled by exam priority."""

    def test_metric_registered_in_scrape(self):
        from prometheus_client import generate_latest
        body = generate_latest().decode()
        assert '# TYPE ris_report_tat_seconds histogram' in body
        assert '# TYPE ris_unbilled_count gauge' in body

    def test_sign_handler_observes_tat(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import AsyncMock, patch
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import User
        from api.telemetry import ris_report_tat_seconds

        class _AuthMW(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.scope['user'] = User({
                    'id': 1, 'permissions': ['REPORT_SIGN'],
                    'tenant': 'default',
                })
                request.scope['auth'] = None
                return await call_next(request)

        from api.reports import ExamReportSignHandler

        app = Starlette(
            routes=[Route('/exams/{exam_id}/sign', endpoint=ExamReportSignHandler, methods=['POST'])],
            middleware=[Middleware(_AuthMW)],
        )
        client = TestClient(app)

        # Reset so the assertion is deterministic.
        ris_report_tat_seconds.clear()

        completed = datetime.now(timezone.utc) - timedelta(minutes=30)
        exam = {
            'id': 'exam-1', 'accession_number': 'ACC-TAT-1',
            'priority': 'stat', 'completed_at': completed,
            'patient_id': 'P1', 'patient_name': 'A',
        }
        report = {
            'id': 'rep-1', 'status': 'final', 'impression': 'x',
            'created_at': completed,
        }

        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(side_effect=[exam, report, report])

        with patch('api.reports.get_conn', return_value=conn), \
             patch('api.reports.ResultsDistributionEngine') as _engine, \
             patch('api.reports.notify_role') as _notify:
            resp = client.post('/exams/exam-1/sign', json={'confirm': True})
        assert resp.status_code == 200, resp.text

        from prometheus_client import generate_latest
        body = generate_latest().decode()
        assert 'ris_report_tat_seconds_bucket{le="+Inf",priority="stat"}' in body
        assert 'ris_report_tat_seconds_sum{priority="stat"}' in body
