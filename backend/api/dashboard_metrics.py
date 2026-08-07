import asyncio
import time

from starlette.endpoints import HTTPEndpoint
from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok
from db.conn import get_conn

from api import telemetry


class DashboardMetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.METRICS_READ)
    async def get(self, request):
        async with get_conn() as conn:
            total_patients = await conn.fetchval('SELECT COUNT(*) FROM patients') or 0
            total_studies = await conn.fetchval('SELECT COUNT(*) FROM studies') or 0
            total_series = await conn.fetchval('SELECT COUNT(*) FROM series') or 0
            total_files = await conn.fetchval('SELECT COUNT(*) FROM files WHERE deleted = FALSE') or 0
            total_users = await conn.fetchval('SELECT COUNT(*) FROM users') or 0
            storage_bytes = await conn.fetchval(
                'SELECT COALESCE(SUM(size), 0)::bigint FROM files WHERE deleted = FALSE'
            ) or 0

            modality_rows = await conn.fetch(
                "SELECT s.modality, COUNT(*) as count FROM files f "
                "JOIN series s ON s.id = f.series_id "
                "WHERE f.deleted = FALSE GROUP BY s.modality ORDER BY count DESC"
            )
            modalities = {row['modality']: row['count'] for row in modality_rows}

            daily_rows = await conn.fetch(
                "SELECT DATE(created) as day, COUNT(*) as count FROM files "
                "WHERE deleted = FALSE AND created >= CURRENT_DATE - INTERVAL '30 days' "
                "GROUP BY day ORDER BY day"
            )
            ingestion = [{'date': str(row['day']), 'count': row['count']} for row in daily_rows]

            latest_files = await conn.fetch(
                "SELECT id, name, created FROM files "
                "WHERE deleted = FALSE ORDER BY created DESC LIMIT 5"
            )

        return ok({
            'totals': {
                'patients': total_patients,
                'studies': total_studies,
                'series': total_series,
                'files': total_files,
                'users': total_users,
                'storage_bytes': storage_bytes,
            },
            'modalities': modalities,
            'ingestion_30d': ingestion,
            'latest_files': [
                {'id': r['id'], 'name': r['name'], 'created': str(r['created'])}
                for r in latest_files
            ],
        })


class DashboardHealthHandler(HTTPEndpoint):
    @requires_permission(Permission.METRICS_READ)
    async def get(self, request):
        results = await asyncio.gather(
            telemetry._check_db(), telemetry._check_es(), telemetry._check_redis(),
            telemetry._check_storage(), telemetry._check_dicom_listener(),
            telemetry._check_ingestion_service(), telemetry._check_hl7_listener(),
            telemetry._check_fhir(), telemetry._check_auth(),
        )
        names = ('database', 'elasticsearch', 'redis', 'storage', 'dicom_listener',
                 'ingestion_service', 'hl7', 'fhir', 'auth')
        components = dict(zip(names, results))
        all_ok = all(c.get('status') == 'ok' for c in components.values())
        state = telemetry._get_state()
        uptime = int(time.time() - (state.start_time if state is not None else time.time()))
        body = {
            'status': 'ok' if all_ok else 'degraded',
            'uptime_seconds': uptime,
            'components': components,
        }
        # mirror health_endpoint: only a failed database probe flips the
        # HTTP status; the body is the same shape in both cases
        http_status = 503 if components['database'].get('status') != 'ok' else 200
        return ok(body, status=http_status)
