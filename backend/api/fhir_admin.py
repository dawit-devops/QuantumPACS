import time
from urllib.parse import urljoin

from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, api_error
from api.schemas.fhir_admin import FhirConfigUpdate, FhirClientCreate, FhirClientUpdate
from api.validate import parse_body
from db.conn import get_conn
from db.fhir_config import FhirConfig
from db.fhir_clients import FhirClient
from log import get_logger

log = get_logger(__name__)


async def _get_fhir_config(conn):
    cfg = FhirConfig(conn)
    raw = await cfg.get_all()
    return {
        'enabled': raw.get('enabled', 'false') == 'true',
        'base_url': raw.get('base_url', 'http://localhost:8080/api/fhir'),
        'publisher': raw.get('publisher', 'QuantumPACS'),
        'max_search_results': int(raw.get('max_search_results', '100')),
        'log_retention_days': int(raw.get('log_retention_days', '30')),
    }


class FhirAdminConfigHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            config = await _get_fhir_config(conn)
        return ok(config)

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def put(self, request):
        data = await parse_body(FhirConfigUpdate, request)
        updates = {}
        if data.enabled is not None:
            updates['enabled'] = 'true' if data.enabled else 'false'
        if data.base_url is not None:
            updates['base_url'] = data.base_url
        if data.publisher is not None:
            updates['publisher'] = data.publisher
        if data.max_search_results is not None:
            updates['max_search_results'] = str(data.max_search_results)
        if data.log_retention_days is not None:
            updates['log_retention_days'] = str(data.log_retention_days)
        if not updates:
            return api_error('NO_CHANGES', 'No changes provided', status=400)
        async with get_conn() as conn:
            cfg = FhirConfig(conn)
            await cfg.set_many(updates)
            config = await _get_fhir_config(conn)
        return ok(config)


class FhirAdminClientsHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            clients = await FhirClient(conn).get_all()
        return ok({'clients': clients})

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def post(self, request):
        data = await parse_body(FhirClientCreate, request)
        async with get_conn() as conn:
            result = await FhirClient(conn).create(
                name=data.name,
                description=data.description,
                redirect_uris=data.redirect_uris,
                grant_type=data.grant_type,
            )
        return created(result)


class FhirAdminClientHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        client_id = request.path_params['id']
        async with get_conn() as conn:
            client = await FhirClient(conn).get_by_id(client_id)
        if not client:
            return api_error('NOT_FOUND', 'Client not found', status=404)
        return ok(client)

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def put(self, request):
        client_id = request.path_params['id']
        data = await parse_body(FhirClientUpdate, request)
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return api_error('NO_CHANGES', 'No changes provided', status=400)
        async with get_conn() as conn:
            fc = FhirClient(conn)
            existing = await fc.get_by_id(client_id)
            if not existing:
                return api_error('NOT_FOUND', 'Client not found', status=404)
            await fc.update_client(client_id, updates)
            client = await fc.get_by_id(client_id)
        return ok(client)

    @requires_permission(Permission.SYSTEM_ADMIN)
    async def delete(self, request):
        client_id = request.path_params['id']
        async with get_conn() as conn:
            fc = FhirClient(conn)
            existing = await fc.get_by_id(client_id)
            if not existing:
                return api_error('NOT_FOUND', 'Client not found', status=404)
            await fc.delete(client_id)
        return JSONResponse({'ok': True})


class FhirAdminMetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        period = request.query_params.get('period', '24h')
        interval_map = {'1h': '1 hour', '24h': '24 hours', '7d': '7 days', '30d': '30 days'}
        interval = interval_map.get(period, '24 hours')

        async with get_conn() as conn:
            volume = await conn.fetch("""
                SELECT
                    resource_type,
                    method,
                    COUNT(*) AS count
                FROM fhir_audit
                WHERE created_at > now() - $1::interval
                GROUP BY resource_type, method
                ORDER BY resource_type, method
            """, interval)

            status_codes = await conn.fetch("""
                SELECT
                    (status_code / 100) * 100 AS status_family,
                    COUNT(*) AS count
                FROM fhir_audit
                WHERE created_at > now() - $1::interval
                GROUP BY status_family
                ORDER BY status_family
            """, interval)

            latency = await conn.fetchrow("""
                SELECT
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY duration_ms) AS p50,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95,
                    percentile_cont(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99
                FROM fhir_audit
                WHERE created_at > now() - $1::interval
            """, interval)

            top_clients = await conn.fetch("""
                SELECT
                    COALESCE(u.email::text, 'system') AS client_name,
                    COUNT(*) AS count
                FROM fhir_audit fa
                LEFT JOIN users u ON u.id = fa.user_id
                WHERE fa.created_at > now() - $1::interval
                GROUP BY u.email
                ORDER BY count DESC
                LIMIT 10
            """, interval)

            total = await conn.fetchval("""
                SELECT COUNT(*) FROM fhir_audit
                WHERE created_at > now() - $1::interval
            """, interval)

            total_errors = await conn.fetchval("""
                SELECT COUNT(*) FROM fhir_audit
                WHERE created_at > now() - $1::interval AND status_code >= 400
            """, interval)

        return ok({
            'period': period,
            'total_requests': total or 0,
            'error_rate': round((total_errors or 0) / max(total or 1, 1) * 100, 2),
            'volume': [dict(r) for r in volume],
            'status_codes': [dict(r) for r in status_codes],
            'latency': {
                'p50': round(latency['p50']) if latency and latency['p50'] else 0,
                'p95': round(latency['p95']) if latency and latency['p95'] else 0,
                'p99': round(latency['p99']) if latency and latency['p99'] else 0,
            },
            'top_clients': [dict(r) for r in top_clients],
        })


class FhirAdminRecentRequestsHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        limit = int(request.query_params.get('limit', '50'))
        offset = int(request.query_params.get('offset', '0'))
        resource_type = request.query_params.get('resource_type', '')
        status_min = request.query_params.get('status_min', '')
        client_id_filter = request.query_params.get('client_id', '')

        conds = []
        vals = []
        idx = 1

        if resource_type:
            conds.append(f'resource_type = ${idx}')
            vals.append(resource_type)
            idx += 1
        if status_min:
            conds.append(f'status_code >= ${idx}')
            vals.append(int(status_min))
            idx += 1
        if client_id_filter:
            conds.append(f'user_id = (SELECT id FROM users WHERE email = ${idx} LIMIT 1)')
            vals.append(client_id_filter)
            idx += 1

        where_clause = ' AND '.join(conds) if conds else 'TRUE'

        async with get_conn() as conn:
            rows = await conn.fetch(f"""
                SELECT
                    fa.id, fa.method, fa.path, fa.query_params,
                    fa.resource_type, fa.resource_id,
                    fa.status_code, fa.duration_ms, fa.ip_address,
                    fa.created_at,
                    COALESCE(u.email::text, 'system') AS caller
                FROM fhir_audit fa
                LEFT JOIN users u ON u.id = fa.user_id
                WHERE {where_clause}
                ORDER BY fa.created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
            """, *vals, limit, offset)

            total = await conn.fetchval(f"""
                SELECT COUNT(*) FROM fhir_audit
                WHERE {where_clause}
            """, *vals)

        return ok({
            'requests': [dict(r) for r in rows],
            'total': total or 0,
            'limit': limit,
            'offset': offset,
        })


class FhirAdminTestHandler(HTTPEndpoint):
    @requires_permission(Permission.SYSTEM_ADMIN)
    async def get(self, request):
        async with get_conn() as conn:
            config = await _get_fhir_config(conn)
        base_url = config['base_url']
        metadata_url = urljoin(base_url.rstrip('/') + '/', 'metadata')

        import httpx
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(metadata_url, headers={'Accept': 'application/fhir+json'})
            elapsed = round((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return ok({
                    'reachable': True,
                    'status_code': resp.status_code,
                    'response_time_ms': elapsed,
                    'fhir_version': resp.json().get('fhirVersion', 'unknown'),
                })
            return ok({
                'reachable': False,
                'status_code': resp.status_code,
                'response_time_ms': elapsed,
                'error': f'Unexpected status code: {resp.status_code}',
            })
        except Exception as e:
            elapsed = round((time.monotonic() - start) * 1000)
            # httpx errors embed URLs/connection internals — bound the text so
            # diagnostic payloads never carry unbounded exception content.
            detail = str(e) or type(e).__name__
            return ok({
                'reachable': False,
                'status_code': 0,
                'response_time_ms': elapsed,
                'error': detail[:200],
            })
