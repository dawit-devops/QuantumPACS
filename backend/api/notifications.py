from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, not_found
from db.conn import get_conn
from db.notifications import Notifications


class NotificationsHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        user_id = request.user.id
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 20))

        async with get_conn() as conn:
            n = Notifications(conn)
            data = await n.get_all(user_id, offset=offset, limit=limit)
            total = await n.count_all(user_id)

        return ok({'data': data, 'total': total})

    @requires_permission(Permission.FILE_READ)
    async def delete(self, request):
        user_id = request.user.id
        async with get_conn() as conn:
            await Notifications(conn).dismiss_all(user_id)
        return ok({})


class NotificationHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def post(self, request):
        nid = request.path_params['id']
        user_id = request.user.id
        async with get_conn() as conn:
            await Notifications(conn).mark_read(nid, user_id)
        return ok({})

    @requires_permission(Permission.FILE_READ)
    async def delete(self, request):
        nid = request.path_params['id']
        user_id = request.user.id
        async with get_conn() as conn:
            await Notifications(conn).dismiss(nid, user_id)
        return ok({})


class NotificationsReadAllHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def post(self, request):
        user_id = request.user.id
        async with get_conn() as conn:
            await Notifications(conn).mark_all_read(user_id)
        return ok({})


class NotificationsUnreadCountHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        user_id = request.user.id
        async with get_conn() as conn:
            count = await Notifications(conn).unread_count(user_id)
        return ok({'count': count})
