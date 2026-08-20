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


class CriticalResultsHandler(HTTPEndpoint):
    """S10-02, S10-07: Critical flag creation and list endpoints."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        recipient_id = request.query_params.get('recipient_id')
        async with get_conn() as conn:
            from db.ris_critical_results import RisCriticalResults
            items = await RisCriticalResults(conn).list_active(
                recipient_id=recipient_id, status=status,
            )
        return ok({'data': items})

    @requires_permission(Permission.REPORT_WRITE)
    async def post(self, request):
        data = await request.json()
        from api.response import validation_error
        if not data.get('finding_description'):
            return validation_error('finding_description is required')
        # S-8: a critical flag must carry patient identity — an alert
        # without an accession/exam or patient is untargetable and worse
        # than none (the old handler accepted any JSON).
        if not (data.get('accession_number') or data.get('exam_id')):
            return validation_error(
                'accession_number or exam_id is required',
            )
        if not (data.get('patient_name') or data.get('patient_id')):
            return validation_error(
                'patient_name or patient_id is required',
            )
        async with get_conn() as conn:
            from db.ris_critical_results import RisCriticalResults
            flag = await RisCriticalResults(conn).create_flag(data, flagged_by=request.user.id)
            from api.notify import notify_role, notify_user
            rec_id = data.get('recipient_id')
            if rec_id:
                await notify_user(
                    conn, rec_id, 'critical.flagged',
                    f"CRITICAL FINDING: {data.get('accession_number', '')}",
                    f"Critical finding flagged for {data.get('patient_name', '')}: {data['finding_description']}",
                    f"/reading/{data.get('exam_id')}",
                )
            else:
                await notify_role(
                    conn, 'radiologist', 'critical.flagged',
                    f"CRITICAL FINDING: {data.get('accession_number', '')}",
                    f"Critical finding flagged for {data.get('patient_name', '')}: {data['finding_description']}",
                    f"/reading/{data.get('exam_id')}",
                )
        return ok({'data': flag})


class CriticalRecipientsHandler(HTTPEndpoint):
    """CR-7: scoped recipient directory for the flag modal picker.

    Clinical roles (radiologist, ED physician) lack USER_READ/ROLE_READ, so a
    lookup by role slug lives here under the same REPORT_WRITE gate as the
    flag POST. Users are listed by role slug only — no tenant/PHI exposure
    beyond the role's membership.
    """

    @requires_permission(Permission.REPORT_WRITE)
    async def get(self, request):
        role = request.query_params.get('role', '')
        async with get_conn() as conn:
            role_row = await conn.fetchrow(
                'SELECT id FROM roles WHERE slug = $1', role,
            )
            if not role_row:
                return ok({'data': []})
            rows = await conn.fetch(
                'SELECT id, username, status FROM users'
                ' WHERE role_id = $1 AND status = $2 ORDER BY username',
                role_row['id'], 'active',
            )
        return ok({'data': [dict(r) for r in rows]})


class CriticalResultAckHandler(HTTPEndpoint):
    """S10-03: Mandatory acknowledgment for critical finding."""

    @requires_permission(Permission.REPORT_READ)
    async def post(self, request):
        critical_id = request.path_params['id']
        async with get_conn() as conn:
            from db.ris_critical_results import RisCriticalResults
            critical_db = RisCriticalResults(conn)
            row = await conn.fetchrow(
                'SELECT id, recipient_id FROM ris_critical_results WHERE id = $1',
                critical_id,
            )
            if not row:
                from api.response import not_found
                return not_found('Critical result entry not found')
            # H12: a non-recipient may only ack when they hold the
            # critical-results permission; a recipient may always ack their
            # own finding.
            is_recipient = str(request.user.id) == str(row['recipient_id'])
            can_override = 'CRITICAL_RESULTS_WRITE' in (request.user.permissions or [])
            if not is_recipient and not can_override:
                from api.response import forbidden
                return forbidden(
                    'Only the designated recipient or a user with '
                    'CRITICAL_RESULTS_WRITE may acknowledge this finding',
                )
            ack = await critical_db.acknowledge(
                critical_id, acknowledged_by=request.user.id,
            )
            if not ack:
                # Not flagged anymore (escalated/cleared/already acked).
                from api.response import not_found
                return not_found(
                    'Critical result is not in a flaggable state to acknowledge',
                )
            from api.tenant_middleware import effective_tenant
            from db.audit_log import AuditLog
            from log import request_id_var
            await AuditLog(conn).log_event(
                event_type='critical.acknowledged',
                actor_id=request.user.id,
                resource_type='critical_result',
                resource_id=critical_id,
                details={'status': ack.get('status')},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': ack})


class DeliveryStatusHandler(HTTPEndpoint):
    """S10-12: Per-recipient result delivery status endpoint."""

    @requires_permission(Permission.REPORT_READ)
    async def get(self, request):
        report_id = request.query_params.get('report_id')
        async with get_conn() as conn:
            # CR-8: select an explicit column list — the ORU payload is PHI
            # and must never be serialized to delivery-status callers.
            rows = await conn.fetch(
                """SELECT id, report_id, accession_number, status, attempts,
                          delivered_at, created_at
                   FROM ris_results_distribution
                   WHERE report_id = $1::uuid ORDER BY created_at DESC""",
                report_id,
            ) if report_id else []
        return ok({'data': [dict(r) for r in rows]})

