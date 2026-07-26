import time
from collections import defaultdict
from typing import Any, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from es import es
from log import request_id_var, tenant_var, user_id_var, trace_id_var, span_id_var, get_logger

log = get_logger(__name__)

_monitor: Any = None


def set_stream_monitor(monitor: Any) -> None:
    global _monitor
    _monitor = monitor


def get_stream_monitor():
    return _monitor


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


_legacy_metrics = {
    'requests_total': defaultdict(int),
    'requests_active': 0,
    'latency_sum': 0.0,
    'latency_count': 0,
}


def record_request(method, path, status_code, elapsed):
    http_requests_total.labels(method=method, path=path, status_code=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(elapsed)
    _legacy_metrics['requests_total'][(method, str(status_code))] += 1
    _legacy_metrics['latency_sum'] += elapsed
    _legacy_metrics['latency_count'] += 1


async def metrics_endpoint(request):
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


_start_time: float = time.time()


def _probe_db():
    from db.conn import get_conn
    return get_conn()


async def _check_db():
    start = time.monotonic()
    try:
        async with _probe_db() as conn:
            val = await conn.fetchval('SELECT 1')
            ok = val == 1
    except Exception as e:
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': str(e)}
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
        return {'status': 'error', 'latency_ms': int((time.monotonic() - start) * 1000), 'message': str(e)}


async def health_endpoint(request):
    db_result = await _check_db()
    es_result = await _check_es()
    components = {
        'database': db_result,
        'elasticsearch': es_result,
    }
    all_ok = all(c.get('status') == 'ok' for c in components.values())
    overall_status = 'ok' if all_ok else 'degraded'
    http_status = 503 if db_result.get('status') != 'ok' else 200
    return JSONResponse({
        'status': overall_status,
        'uptime_seconds': int(time.time() - _start_time),
        'components': components,
    }, status_code=http_status)
