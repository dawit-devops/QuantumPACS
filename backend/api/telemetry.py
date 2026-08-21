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
# RIS interface engine (S3-04, spec §10.4): the failure-rate SLO alert
# divides rate{status="FAILED"} by the RECEIVED total, so the engine
# counts RECEIVED once per message and PROCESSED/FAILED as terminal
# states (retries re-increment their terminal state).
ris_hl7_messages_total = Counter(
    'ris_hl7_messages_total', 'HL7 messages processed',
    ['type', 'trigger', 'status'],
)
ris_hl7_message_latency_seconds = Histogram(
    'ris_hl7_message_latency_seconds', 'HL7 message processing latency',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
# S6-11 / RIS-SL-22: MPPS → tracking latency (< 5s p95). Per-message
# processing time in the MPPS consumer, labelled by event type so the
# N-CREATE and N-SET paths are distinguishable.
ris_mpps_latency_seconds = Histogram(
    'ris_mpps_latency_seconds', 'MPPS message processing latency',
    ['event_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
# S11-14 / spec §10.4: charge-capture rate. The latency histogram drives the
# sign-to-charge drop SLO; the gauge feeds the RISUnbilledAging alert
# (unbilled count > 0 for 5d).
ris_charge_drop_latency_seconds = Histogram(
    'ris_charge_drop_latency_seconds', 'Time from sign to charge drop',
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)
ris_unbilled_count = Gauge(
    'ris_unbilled_count', 'Number of unbilled (PENDING) charges',
)
# S12-33 / RIS-SL-30/31/32: report turnaround time (exam completed -> signed),
# labelled by priority so the manager dashboard can show STAT vs routine TAT.
ris_report_tat_seconds = Histogram(
    'ris_report_tat_seconds', 'Report turnaround time from exam completion to sign',
    ['priority'],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 180.0, 600.0, 1800.0, 3600.0, 10800.0),
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
    # Database stores the (traced) pool as `_pool`; the _TracedPool wrapper
    # forwards get_idle_size/get_active_size to the underlying asyncpg pool.
    pool = db._pool
    if pool is None:
        return
    try:
        idle = pool.get_idle_size()
        # asyncpg Pool exposes no get_active_size — active = size - idle.
        in_use = max(0, pool.get_size() - idle)
        db_connections_available.labels(tenant='default').set(idle)
        db_connections_in_use.labels(tenant='default').set(in_use)
    except Exception:
        pass


async def metrics_endpoint(request):
    from config import config
    if not config.get('prometheus_enabled', True):
        from starlette.responses import PlainTextResponse
        return PlainTextResponse('Metrics disabled', status_code=404)
    # Admin gate lives here, on the endpoint, not in TokenAuth._PUBLIC_PATHS:
    # metrics must stay authenticated (they can leak endpoint cardinality and
    # request volumes) but the guard must produce a proper forbidden()
    # envelope for non-admins instead of a bare HTTPException with no detail.
    user = request.scope.get('user')
    if not user or not getattr(user, 'is_authenticated', False) or not user.admin:
        from api.response import forbidden
        return forbidden('Admin access required')
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
    except Exception:
        # Stable, non-leaking message: the raw asyncpg error string can embed
        # host/user/port details of the failed connection, so the public
        # health payload exposes only the failure class, never the exception.
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Database unreachable'}
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
    except Exception:
        # Same contract as _check_db: the raw exception can embed connection
        # internals (hosts, ports, backends), so only the stable failure
        # class ever reaches the public health payload.
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Elasticsearch unreachable'}


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
    except Exception:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Redis unreachable'}


async def _check_storage():
    start = time.monotonic()
    try:
        from db.conn import get_conn
        async with get_conn() as conn:
            rows = await conn.fetch("SELECT id, type, master FROM replicas")
        # Replica/backend types (local/s3/b2) reveal storage topology — the
        # health payload only reports reachability.
        masters = [r['type'] for r in rows if r.get('master')]
        if masters:
            return {'status': 'ok', 'latency_ms': int((time.monotonic() - start) * 1000)}
        return {'status': 'degraded', 'latency_ms': 0, 'message': 'No master replica configured'}
    except Exception:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Storage backend unreachable'}


async def _check_dicom_listener():
    from config import config
    port = int(config.get('dicom_cstore_port', '11112'))
    try:
        import socket
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            pass
        state = _get_state()
        start = state.start_time if state is not None else time.time()
        # The listener port is an internal deployment detail — not exposed.
        return {'status': 'ok', 'uptime_seconds': int(time.time() - start), 'latency_ms': 0}
    except Exception:
        return {'status': 'degraded', 'uptime_seconds': 0, 'latency_ms': 0, 'message': 'DICOM listener not reachable'}


async def _check_ingestion_service():
    try:
        monitor = get_stream_monitor()
        if monitor is None:
            return {'status': 'degraded', 'stream_lag': -1, 'message': 'Stream monitor not started'}
        metrics = monitor.metrics()
        total_pending = sum(info.get('pending', 0) for info in metrics.values())
        return {'status': 'ok', 'stream_lag': total_pending}
    except Exception:
        return {'status': 'error', 'stream_lag': -1, 'message': 'Ingestion service unreachable'}


async def _check_hl7_listener():
    from config import config
    port = int(config.get('hl7_mllp_port', '12579'))
    try:
        import socket
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            pass
        return {'status': 'ok', 'latency_ms': 0}
    except Exception:
        return {'status': 'degraded', 'latency_ms': 0, 'message': 'HL7 MLLP listener not reachable'}


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
    except Exception:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'FHIR configuration unreachable'}


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
    except Exception:
        return {'status': 'degraded',
                'latency_ms': int((time.monotonic() - start) * 1000),
                'message': 'Token blocklist fail-open active (redis unreachable)'}


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
