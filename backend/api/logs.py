from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import paginated
from db.conn import get_conn
from db.log import Log


class LogsHandler(HTTPEndpoint):
    @requires_permission(Permission.LOG_READ)
    async def get(self, request):
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 20))

        async with get_conn() as conn:
            data = await Log(conn).get_logs(offset=offset, limit=limit)
            total = await Log(conn).count_logs()

        return paginated(
            [dict(u) for u in data],
            total=total, page=(offset // limit) + 1, per_page=limit,
            request=request,
        )
