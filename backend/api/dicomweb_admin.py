from starlette.endpoints import HTTPEndpoint

import json

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok
from api.dicomweb import VALID_MODALITIES
from db.conn import get_conn
from db.hl7_message import period_to_interval
from log import get_logger

log = get_logger(__name__)

_PERIODS = {'24h': '24 hours', '7d': '7 days', '30d': '30 days'}


def _get_qido_search_params():
    return [
        {'name': 'PatientID', 'type': 'string', 'description': 'Patient identifier'},
        {'name': 'PatientName', 'type': 'string', 'description': 'Patient name (exact or wildcard)'},
        {'name': 'AccessionNumber', 'type': 'string', 'description': 'Study accession number'},
        {'name': 'StudyInstanceUID', 'type': 'string', 'description': 'Study instance UID'},
        {'name': 'limit', 'type': 'integer', 'description': 'Max results (default 100)'},
        {'name': 'offset', 'type': 'integer', 'description': 'Result offset'},
    ]


def _get_wado_features():
    return {
        'retrieve_study': True,
        'retrieve_series': True,
        'retrieve_instance': True,
        'retrieve_metadata': False,
        'retrieve_bulkdata': False,
        'transfer_syntax': 'as_stored',
        'accept_header': 'multipart/related; type=application/dicom',
    }


class DicomWebAdminHandler(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        return ok({
            'qido': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies', 'method': 'GET', 'description': 'Search studies'},
                    {'path': '/dicomweb/studies/{study_uid}/series', 'method': 'GET', 'description': 'List series'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}/instances', 'method': 'GET', 'description': 'List instances'},
                ],
                'search_params': _get_qido_search_params(),
                'response_format': 'application/dicom+json',
                'pagination': 'limit/offset with X-Total-Count header',
            },
            'wado': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies/{study_uid}', 'method': 'GET', 'description': 'Retrieve study'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}', 'method': 'GET', 'description': 'Retrieve series'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}', 'method': 'GET', 'description': 'Retrieve instance'},
                    {'path': '/wado', 'method': 'GET', 'description': 'WADO-URI retrieval'},
                ],
                'features': _get_wado_features(),
            },
            'stow': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies', 'method': 'POST', 'description': 'Store instances'},
                ],
                'content_type': 'multipart/related; type=application/dicom',
                'modality_validation': True,
                'valid_modalities_count': len(VALID_MODALITIES),
            },
            'modalities': sorted(VALID_MODALITIES),
            'missing_features': [
                'Study metadata (GET /studies/{uid}/metadata)',
                'Series metadata (GET .../series/{uid}/metadata)',
                'Instance metadata (GET .../instances/{uid}/metadata)',
                'Bulk data URI support',
                'Transfer syntax negotiation',
            ],
        })


class DicomWebRequestsHandler(HTTPEndpoint):
    """Browsable view of the dicomweb.request audit rows.

    Cursor-paginated like the generic /logs endpoint, but pre-scoped to the
    DICOMweb service traffic recorded by DicomWebLogMiddleware. Optional
    kind/status filters and a metrics-style period scope.
    """

    _KINDS = frozenset({'qido', 'wado', 'stow', 'frames', 'archive', 'wado_uri'})

    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        kind = request.query_params.get('kind')
        status_filter = request.query_params.get('status')
        period_key = request.query_params.get('period', '')
        cursor = request.query_params.get('cursor')
        if cursor and cursor.lower() in ('null', 'none', ''):
            cursor = None
        limit = int(request.query_params.get('limit', 50))
        limit = max(10, min(200, limit))

        where = ["l.log LIKE '%dicomweb.request%'"]
        params = []
        idx = 1
        if kind in self._KINDS:
            where.append(f"(l.log::json -> 'detail') ->> 'kind' = ${idx}")
            params.append(kind)
            idx += 1
        if status_filter and status_filter.isdigit():
            where.append(f"(l.log::json -> 'detail' ->> 'status')::int = ${idx}")
            params.append(int(status_filter))
            idx += 1
        if period_key in _PERIODS:
            where.append(f"l.created > now() - ${idx}::interval")
            params.append(period_to_interval(_PERIODS[period_key]))
            idx += 1
        if cursor:
            where.append(f"l.id < ${idx}")
            params.append(int(cursor))
            idx += 1
        where_sql = ' AND '.join(where)

        async with get_conn() as conn:
            rows = await conn.fetch(f"""
                SELECT l.id, l.created, l.log, l.tenant, l.request_id, l.trace_id
                FROM logs l
                WHERE {where_sql}
                ORDER BY l.id DESC
                LIMIT ${idx}
            """, *params, limit)
            total = await conn.fetchval(f"""
                SELECT COUNT(*) FROM logs l WHERE {where_sql}
            """, *params) or 0

        data = []
        for row in rows:
            payload = json.loads(row['log']) if isinstance(row['log'], str) else {}
            detail = payload.get('detail') or {}
            data.append({
                'id': row['id'],
                'created_at': str(row['created']) if row.get('created') else None,
                'kind': detail.get('kind'),
                'method': detail.get('method'),
                'path': detail.get('path'),
                'status': detail.get('status'),
                'duration_ms': detail.get('duration_ms'),
                'actor': payload.get('actor'),
                'tenant': row.get('tenant'),
                'request_id': row.get('request_id'),
                'trace_id': row.get('trace_id'),
            })

        next_cursor = data[-1]['id'] if len(data) == limit else None
        return ok({
            'data': data,
            'next_cursor': next_cursor,
            'has_more': len(data) == limit,
            'total': total,
        })


class DicomWebMetricsHandler(HTTPEndpoint):
    """DICOM ingest/archive metrics for the admin dashboard.

    `period=24h|7d|30d` scopes the stored counters; the error counter reads
    the store-failure log rows written by dcm/store.py (dicom.store_error).
    """

    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        period_key = request.query_params.get('period', '24h')
        interval = period_to_interval(_PERIODS.get(period_key, '24 hours'))

        async with get_conn() as conn:
            files_period = await conn.fetchval(
                "SELECT COUNT(*) FROM files"
                " WHERE deleted = FALSE AND created > now() - $1::interval",
                interval,
            )
            studies_period = await conn.fetchval(
                "SELECT COUNT(*) FROM studies"
                " WHERE created_at > now() - $1::interval",
                interval,
            )
            failed_stores = await conn.fetchval(
                "SELECT COUNT(*) FROM logs"
                " WHERE created > now() - $1::interval"
                " AND log LIKE '%dicom.store_error%'",
                interval,
            )
            storage_bytes = await conn.fetchval(
                "SELECT COALESCE(SUM(size), 0)::bigint FROM files WHERE deleted = FALSE"
            ) or 0
            modality_rows = await conn.fetch(
                "SELECT s.modality, COUNT(*) AS count FROM files f"
                " JOIN series s ON s.id = f.series_id"
                " WHERE f.deleted = FALSE AND f.created > now() - $1::interval"
                " GROUP BY s.modality ORDER BY count DESC",
                interval,
            )
            request_rows = await conn.fetch(
                "SELECT (l.log::json -> 'detail') ->> 'kind' AS kind,"
                "       COUNT(*) AS total,"
                "       COUNT(*) FILTER (WHERE (l.log::json -> 'detail' ->> 'status')::int >= 400) AS errors"
                " FROM logs l"
                " WHERE l.log LIKE '%dicomweb.request%'"
                "   AND l.created > now() - $1::interval"
                " GROUP BY kind ORDER BY total DESC",
                interval,
            )
            totals = await conn.fetchrow(
                "SELECT (SELECT COUNT(*) FROM studies) AS studies,"
                "       (SELECT COUNT(*) FROM series) AS series,"
                "       (SELECT COUNT(*) FROM files) AS files"
            )
        request_rows = [dict(r) for r in request_rows]
        return ok({
            'period': period_key,
            'files_stored': files_period or 0,
            'studies_stored': studies_period or 0,
            'failed_stores': failed_stores or 0,
            'storage_bytes': storage_bytes,
            'by_modality': [dict(r) for r in modality_rows],
            'requests_total': sum(r['total'] for r in request_rows),
            'requests_failed': sum(r['errors'] for r in request_rows),
            'requests_by_kind': request_rows,
            'totals': {
                'studies': totals['studies'] or 0,
                'series': totals['series'] or 0,
                'files': totals['files'] or 0,
            },
        })
