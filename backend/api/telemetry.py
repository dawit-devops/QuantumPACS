import time
from collections import defaultdict

from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from es import es
from log import request_id_var, get_logger

log = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get('X-Request-ID', '')
        request_id_var.set(rid)
        response = await call_next(request)
        if rid:
            response.headers['X-Request-ID'] = rid
        return response


_metrics = {
    'requests_total': defaultdict(int),
    'requests_active': 0,
    'latency_sum': 0.0,
    'latency_count': 0,
}


def record_request(method, path, status_code, elapsed):
    _metrics['requests_total'][(method, str(status_code))] += 1
    _metrics['latency_sum'] += elapsed
    _metrics['latency_count'] += 1


async def metrics_endpoint(request):
    total = sum(_metrics['requests_total'].values())
    avg_latency = _metrics['latency_sum'] / _metrics['latency_count'] if _metrics['latency_count'] else 0.0
    return JSONResponse({
        'requests_total': total,
        'requests_by_status': {
            f'{method} {code}': count
            for (method, code), count in sorted(_metrics['requests_total'].items())
        },
        'average_latency_seconds': round(avg_latency, 4),
    })


async def health_endpoint(request):
    db_ok = False
    db_error = None
    es_ok = False
    es_error = None
    try:
        from db.conn import get_conn
        async with get_conn() as conn:
            val = await conn.fetchval('SELECT 1')
            db_ok = val == 1
    except Exception as e:
        db_error = str(e)

    try:
        es_client = es.get_client()
        if es_client:
            es_ok = await es_client.ping()
        else:
            es_ok = False
            es_error = 'not configured'
    except Exception as e:
        es_error = str(e)

    status = 503 if not db_ok else 200
    return JSONResponse({
        'status': 'ok' if (db_ok and es_ok) else 'degraded',
        'database': 'connected' if db_ok else f'error: {db_error}',
        'elasticsearch': 'connected' if es_ok else f'error: {es_error}',
    }, status_code=status)
