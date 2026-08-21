"""RIS Reminders API (R2-02).

Send a reminder over the channel service, read the delivery audit log, and
manage per-event reminder config (channel, template, lead time, active).
The message-log FAILED rows feed the <= 5-minute failure alert (R2-01-13);
the config `active` flag is the patient-facing opt-out gate (R2-01-12).
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, validation_error
from api.validate import parse_body
from api.schemas.ris_reminders import (
    SendReminderRequest,
    ReminderConfigRequest,
)
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class ReminderSendHandler(HTTPEndpoint):
    """R2-01-11: POST /ris/reminders/send — dispatch one reminder."""

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        body = await parse_body(SendReminderRequest, request)
        tenant = effective_tenant(request) or 'default'
        from services.reminders.service import ReminderDeliveryError, ReminderService
        try:
            result = await ReminderService().send(
                event_type=body.event_type,
                recipient=body.recipient,
                channel=body.channel,
                subject=body.subject,
                body=body.body,
                tenant_id=tenant,
            )
        except ReminderDeliveryError as exc:
            return validation_error(str(exc))
        if result.get('status') == 'FAILED':
            return validation_error(
                f'Delivery failed after {result.get("attempts")} attempts')
        return created(result)


class ReminderLogHandler(HTTPEndpoint):
    """R2-01-13: GET /ris/reminders/log — send/receipt audit trail."""

    @requires_permission(Permission.PRIOR_AUTH_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        try:
            page = max(1, int(request.query_params.get('page', '1')))
            per_page = min(200, max(1, int(request.query_params.get('per_page', '50'))))
        except (TypeError, ValueError):
            return validation_error('Invalid pagination parameters')
        async with get_conn() as conn:
            from db.ris_message_log import MessageLog
            rows, total = await MessageLog(conn).list(
                tenant, status=status, limit=per_page, offset=(page - 1) * per_page)
        return ok({'data': rows, 'total': total, 'page': page, 'per_page': per_page})


class ReminderConfigHandler(HTTPEndpoint):
    """R2-01-10: GET /ris/reminders/config and POST (upsert)."""

    @requires_permission(Permission.PRIOR_AUTH_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_message_log import ReminderConfig
            rows = await ReminderConfig(conn).list_active(tenant)
        return ok({'data': [dict(r) for r in rows]})

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        body = await parse_body(ReminderConfigRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_message_log import ReminderConfig
            await ReminderConfig(conn).upsert(
                event_type=body.event_type,
                channel=body.channel,
                template=body.template,
                lead_time_hours=body.lead_time_hours,
                active=body.active,
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='reminder.config_updated',
                actor_id=request.user.id,
                resource_type='ris_reminder_config',
                resource_id=body.event_type,
                tenant=tenant,
            )
        return ok({'event_type': body.event_type, 'status': 'updated'})
