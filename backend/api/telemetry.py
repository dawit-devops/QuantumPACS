import asyncio
import time
from collections import defaultdict
from typing import Any

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from es import es
from log import request_id_var, tenant_var, user_id_var, trace_id_var, span_id_var, get_logger

log = get_logger(__name__)

_app = None


def set_app(app):
    global _app
    _app = app


def get_app():
    return _app


def _get_state():
    if _app is None:
        return None
    if not hasattr(_app.state, 'telemetry_state'):
        _app.state.telemetry_state = TelemetryState()
    return _app.state.telemetry_state


class TelemetryState:
    def __init__(self):
        self.monitor: Any = None
        self.start_time: float = time.time()
        self.legacy_metrics: dict = {
            'requests_total': defaultdict(int),
            'requests_active': 0,
            'latency_sum': 0.0,
            'latency_count': 0,
        }


def set_stream_monitor(monitor: Any) -> None:
    state = _get_state()
    if state is not None:
        state.monitor = monitor


def get_stream_monitor():
    state = _get_state()
    if state is None:
        return None
    return state.monitor


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get('X-Request-ID', '')
        request_id_var.set(rid)
        tenant_var.set(request.headers.get('X-Tenant-ID', ''))
        user_id_var.set(request.headers.get('X-User-ID', ''))
        trace_id_var.set(request.headers.get('X-Trace-ID', ''))
        span_id_var.set(request.headers.get('X-Span-ID', ''))
        response = await call_next(request)
        if rid:
            response.headers['X-Request-ID'] = rid
        if request.headers.get('X-Trace-ID'):
            response.headers['X-Trace-ID'] = request.headers['X-Trace-ID']
        return response


http_requests_total = Counter(
    'http_requests_total', 'Total HTTP requests',
    ['method', 'path', 'status_code'],
)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds', 'HTTP request duration in seconds',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
http_requests_in_progress = Gauge(
    'http_requests_in_progress', 'HTTP requests currently in progress',
    ['method', 'path'],
)
db_connections_available = Gauge(
    'db_connections_available', 'Database connections available in pool',
    ['tenant'],
)
db_connections_in_use = Gauge(
    'db_connections_in_use', 'Database connections currently in use',
    ['tenant'],
)
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds', 'Database query duration in seconds',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
redis_stream_lag_seconds = Gauge(
    'redis_stream_lag_seconds', 'Redis stream consumer lag',
    ['stream', 'consumer_group'],
)
dicom_cstore_throughput_bytes = Counter(
    'dicom_cstore_throughput_bytes', 'Total bytes received via DICOM C-STORE',
)
dicomweb_requests_total = Counter(
    'dicomweb_requests_total', 'Total DICOMweb requests',
    ['method', 'resource'],
)


def record_request(method, path, status_code, elapsed):
    state = _get_state()
    http_requests_total.labels(method=method, path=path, status_code=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(elapsed)
    if '/dicomweb/' in path:
        resource = path.split('/dicomweb/')[1].split('/')[0]
        dicomweb_requests_total.labels(method=method, resource=resource).inc()
    if state is not None:
        state.legacy_metrics['requests_total'][(method, str(status_code))] += 1
        state.legacy_metrics['latency_sum'] += elapsed
        state.legacy_metrics['latency_count'] += 1


def _sample_db_pool():
    from db.conn import get_database
    db = get_database()
    pool = db.pool
    if pool is None:
        return
    try:
        idle = pool.get_idle_size()
        in_use = pool.get_active_size()
        db_connections_available.labels(tenant='default').set(idle)
        db_connections_in_use.labels(tenant='default').set(in_use)
    except Exception:
        pass


async def metrics_endpoint(request):
    from config import config
    if not config.get('prometheus_enabled', True):
        from starlette.responses import PlainTextResponse
        return PlainTextResponse('Metrics disabled', status_code=404)
    if 'user' in request.scope:
        from api.utils import is_admin
        is_admin(request)
    _sample_db_pool()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)





def _probe_db():
    from db.conn import get_conn
    return get_conn()


async def _check_db():
    start = time.monotonic()
    try:
        async with _probe_db() as conn:
            await conn.fetchval('SELECT 1')
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': (str(e) or type(e).__name__)[:200]}
    return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000)}


async def _check_es():
    start = time.monotonic()
    try:
        ec = es.get_client()
        if ec:
            ok = await ec.ping()
            latency = int((time.monotonic() - start) * 1000)
            if ok:
                return {'status': 'ok', 'latency_ms': latency}
            return {'status': 'error', 'latency_ms': latency, 'message': 'ping returned false'}
        return {'status': 'degraded', 'latency_ms': 0, 'message': 'ES unavailable, search fallback active'}
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': (str(e) or type(e).__name__)[:200]}


async def _check_redis():
    start = time.monotonic()
    try:
        from api.redis_client import get_client, is_available
        if not is_available():
            return {'status': 'degraded', 'latency_ms': 0, 'message': 'Redis not configured'}
        client = await get_client()
        if client:
            await client.ping()
            return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000)}
        return {'status': 'degraded', 'latency_ms': 0, 'message': 'Redis unavailable'}
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': (str(e) or type(e).__name__)[:200]}


async def _check_storage():
    start = time.monotonic()
    try:
        from db.conn import get_conn
        async with get_conn() as conn:
            rows = await conn.fetch("SELECT id, type, master FROM replicas")
        masters = [r['type'] for r in rows if r.get('master')]
        backends = list({r['type'] for r in rows})
        if masters:
            return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000), 'master': masters[0], 'replicas': backends}
        return {'status': 'degraded', 'latency_ms': 0, 'replicas': backends, 'message': 'No master replica configured'}
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': (str(e) or type(e).__name__)[:200]}


async def _check_dicom_listener():
    from config import config
    port = int(config.get('dicom_cstore_port', '11112'))
    try:
        import socket
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            pass
        state = _get_state()
        start = state.start_time if state is not None else time.time()
        return {'status': 'ok', 'port': port, 'uptime_seconds': int(time.time() - start), 'latency_ms': 0}
    except Exception:
        return {'status': 'degraded', 'port': port, 'uptime_seconds': 0, 'latency_ms': 0, 'message': 'DICOM listener not reachable'}


async def _check_ingestion_service():
    try:
        monitor = get_stream_monitor()
        if monitor is None:
            return {'status': 'degraded', 'stream_lag': -1, 'message': 'Stream monitor not started'}
        metrics = monitor.metrics()
        total_pending = sum(info.get('pending', 0) for info in metrics.values())
        return {'status': 'ok', 'stream_lag': total_pending}
    except Exception as e:
        return {'status': 'error', 'stream_lag': -1, 'message': (str(e) or type(e).__name__)[:200]}


async def _check_hl7_listener():
    from config import config
    port = int(config.get('hl7_mllp_port', '12579'))
    try:
        import socket
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            pass
        return {'status': 'ok', 'port': port, 'latency_ms': 0}
    except Exception:
        return {'status': 'degraded', 'port': port, 'latency_ms': 0, 'message': 'HL7 MLLP listener not reachable'}


async def _check_fhir():
    start = time.monotonic()
    try:
        from db.conn import get_conn
        from db.fhir_config import FhirConfig
        async with get_conn() as conn:
            raw = await FhirConfig(conn).get_all()
        latency = int((time.monotonic() - start) * 1000)
        if raw.get('enabled', 'false') == 'true':
            return {'status': 'ok', 'latency_ms': latency}
        return {'status': 'degraded', 'latency_ms': latency, 'message': 'FHIR not enabled (fhir_config.enabled != true)'}
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': (str(e) or type(e).__name__)[:200]}


async def _check_auth():
    start = time.monotonic()
    try:
        from config import assert_production_secret
        assert_production_secret()
    except Exception:
        return {'status': 'degraded', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Auth secret is unset or still the default placeholder'}
    return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000)}


async def _check_token_blocklist():
    """R2-07: the token blocklist is fail-open by design — auth keeps working
    without Redis, and the HTTP contract never 503s over it. Its degradation
    must still be observable: surfaced as its own 'degraded' component here
    instead of being hidden inside the auth component."""
    start = time.monotonic()
    try:
        from api.redis_client import get_client, is_available
        if not is_available():
            return {'status': 'degraded', 'latency_ms': 0,
                    'message': 'Token blocklist fail-open active (redis unavailable)'}
        client = await get_client(db=1)
        if client is None:
            return {'status': 'degraded',
                    'latency_ms': int((time.monotonic() - start) * 1000),
                    'message': 'Token blocklist fail-open active (redis client unavailable)'}
        await client.ping()
        return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000)}
    except Exception as e:
        return {'status': 'degraded',
                'latency_ms': int((time.monotonic() - start) * 1000),
                'message': f'Token blocklist fail-open active: {(str(e) or type(e).__name__)[:200]}'}


async def health_endpoint(request):
    db_result, es_result, redis_result, storage_result, dicom_result, ingestion_result, hl7_result, fhir_result, auth_result, blocklist_result = await asyncio.gather(
        _check_db(), _check_es(), _check_redis(), _check_storage(),
        _check_dicom_listener(), _check_ingestion_service(),
        _check_hl7_listener(), _check_fhir(), _check_auth(),
        _check_token_blocklist(),
    )
    components = {
        'database': db_result,
        'elasticsearch': es_result,
        'redis': redis_result,
        'storage': storage_result,
        'dicom_listener': dicom_result,
        'ingestion_service': ingestion_result,
        'hl7': hl7_result,
        'fhir': fhir_result,
        'auth': auth_result,
        'token_blocklist': blocklist_result,
    }
    all_ok = all(c.get('status') == 'ok' for c in components.values())
    overall_status = 'ok' if all_ok else 'degraded'
    http_status = 503 if db_result.get('status') != 'ok' else 200
    state = _get_state()
    uptime = int(time.time() - (state.start_time if state is not None else time.time()))
    return JSONResponse({
        'status': overall_status,
        'uptime_seconds': uptime,
        'components': components,
    }, status_code=http_status)
