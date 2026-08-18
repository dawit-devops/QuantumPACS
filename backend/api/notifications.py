from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, api_error
from api.validate import parse_body
from api.schemas.notifications import NotificationPrefsRequest
from db.conn import get_conn
from db.notifications import Notifications
from db.notification_prefs import NotificationPrefs


class NotificationPreferencesHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        """Return explicit prefs plus role-default resolution per event type."""
        user_id = request.user.id
        async with get_conn() as conn:
            prefs = NotificationPrefs(conn)
            explicit = await prefs.get(user_id)
        defaults = {
            et: NotificationPrefs.default_enabled(
                getattr(request.user, 'role_slug', ''), et,
            )
            for et in NotificationPrefs.EVENT_CATALOG
        }
        merged = {
            et: explicit.get(et, defaults[et]) for et in NotificationPrefs.EVENT_CATALOG
        }
        return ok({
            'preferences': merged,
            'explicit': explicit,
            'role_defaults': defaults,
        })

    @requires_permission(Permission.FILE_READ)
    async def put(self, request):
        body = await parse_body(NotificationPrefsRequest, request)
        user_id = request.user.id
        async with get_conn() as conn:
            prefs = NotificationPrefs(conn)
            known = set(NotificationPrefs.EVENT_CATALOG)
            unknown = set(body.preferences) - known
            if unknown:
                return api_error(
                    'VALIDATION',
                    f'Unknown event types: {", ".join(sorted(unknown))}',
                    status=422,
                )
            await prefs.set(user_id, body.preferences)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='user.notification_prefs_changed',
                actor_id=user_id,
                resource_type='user',
                resource_id=str(user_id),
                details={'description': 'Notification preferences updated'},
            )
        return ok({'updated': sorted(body.preferences)})


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
