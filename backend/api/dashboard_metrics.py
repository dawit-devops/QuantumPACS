from starlette.endpoints import HTTPEndpoint
from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok
from db.conn import get_conn


class DashboardMetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.METRICS_READ)
    async def get(self, request):
        async with get_conn() as conn:
            total_patients = await conn.fetchval('SELECT COUNT(*) FROM patients') or 0
            total_studies = await conn.fetchval('SELECT COUNT(*) FROM studies') or 0
            total_series = await conn.fetchval('SELECT COUNT(*) FROM series') or 0
            total_files = await conn.fetchval('SELECT COUNT(*) FROM files WHERE deleted = FALSE') or 0
            total_users = await conn.fetchval('SELECT COUNT(*) FROM users') or 0
            # the files table has no size column (not tracked on ingest), so
            # storage is reported as 0 until sizes are recorded at upload time
            storage_bytes = 0

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
