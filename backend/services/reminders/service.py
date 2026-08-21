"""RIS Reminder Service (R2-02, E-RIS2-02).

Dispatches outbound reminders over channel stubs (SMS/email/phone),
honoring opt-out, recording every delivery in ris_message_log, and
retrying failures. The provider layer is a stub (no real Twilio/SES
credentials in dev): each channel validates the recipient shape and
simulates a send, returning a provider receipt. Production adapters slot
in behind the same interface.

Opt-out (R2-01-12): a reminder for a user-scoped event consults
notification_prefs per event_type; patient-facing reminders are gated by
the reminder_config `active` flag + a non-empty recipient. The
ris_message_log FAILED rows feed the <= 5-minute failure alert (R2-01-13).
"""

import asyncio

from db.conn import get_conn
from db.ris_message_log import MessageLog, ReminderConfig


class ReminderDeliveryError(Exception):
    pass


class _SmsChannel:
    name = 'sms'

    def validate(self, recipient):
        if not recipient:
            raise ReminderDeliveryError('SMS recipient (phone) is empty')
        digits = ''.join(ch for ch in str(recipient) if ch.isdigit())
        if len(digits) < 10:
            raise ReminderDeliveryError('SMS recipient must be a 10+ digit phone')

    async def send(self, recipient, subject, body, tenant_id):
        self.validate(recipient)
        return f'sms-{recipient[-4:]}'


class _EmailChannel:
    name = 'email'

    def validate(self, recipient):
        if '@' not in str(recipient):
            raise ReminderDeliveryError('Email recipient must be an address')

    async def send(self, recipient, subject, body, tenant_id):
        self.validate(recipient)
        return f'email-{hash(recipient) % 100000:06d}'


class _PhoneChannel:
    name = 'phone'

    def validate(self, recipient):
        digits = ''.join(ch for ch in str(recipient) if ch.isdigit())
        if len(digits) < 10:
            raise ReminderDeliveryError('Phone recipient must be a 10+ digit number')

    async def send(self, recipient, subject, body, tenant_id):
        self.validate(recipient)
        return f'phone-{recipient[-4:]}'


CHANNELS = {
    'sms': _SmsChannel(),
    'email': _EmailChannel(),
    'phone': _PhoneChannel(),
}


class ReminderService:
    """Outbound reminder dispatch with retry + delivery audit."""

    def __init__(self, max_attempts=3):
        self.max_attempts = int(max_attempts or 3)

    async def send(self, *, event_type, recipient, channel='email',
                   subject='', body='', tenant_id='default'):
        """Send one reminder, honoring opt-out; returns the log row.

        Raises ReminderDeliveryError when opt-out is active (nothing sent).
        """
        if not await self._opt_out_allowed(event_type, tenant_id):
            raise ReminderDeliveryError(f'Opted out of {event_type} reminders')
        channel_svc = CHANNELS.get(channel)
        if channel_svc is None:
            raise ReminderDeliveryError(f'Unknown channel: {channel}')

        async with get_conn() as conn:
            log = MessageLog(conn)
            attempt = 1
            while attempt <= self.max_attempts:
                try:
                    receipt = await channel_svc.send(recipient, subject, body, tenant_id)
                    row = await log.log_sent(
                        channel=channel, recipient=str(recipient),
                        event_type=event_type, subject=subject, body=body,
                        provider_receipt=receipt, tenant_id=tenant_id,
                    )
                    return {'id': row['id'], 'status': 'SENT', 'attempts': attempt}
                except ReminderDeliveryError as exc:
                    # Validation errors are permanent — don't retry.
                    await log.log_failed(
                        channel=channel, recipient=str(recipient),
                        event_type=event_type, subject=subject, body=body,
                        attempts=attempt, tenant_id=tenant_id,
                    )
                    raise ReminderDeliveryError(str(exc)) from exc
                except Exception:
                    if attempt < self.max_attempts:
                        await asyncio.sleep(0.1 * attempt)
                        attempt += 1
                        continue
                    row = await log.log_failed(
                        channel=channel, recipient=str(recipient),
                        event_type=event_type, subject=subject, body=body,
                        attempts=attempt, tenant_id=tenant_id,
                    )
                    return {'id': row['id'], 'status': 'FAILED', 'attempts': attempt}
        raise ReminderDeliveryError('no connection')

    async def _opt_out_allowed(self, event_type, tenant_id):
        """Reminder config `active` gates the event (patient opt-out).

        A user-level opt-out for the same event_type lives in
        notification_prefs and is consulted by callers that have a user;
        this service-level gate covers patient/contact reminders.
        """
        async with get_conn() as conn:
            cfg = await ReminderConfig(conn).get(event_type, tenant_id)
            return cfg is not None and bool(cfg['active'])

    async def failed_since(self, minutes=5, tenant_id='default'):
        """FAILED deliveries in the window (R2-01-13 alert input)."""
        async with get_conn() as conn:
            return await MessageLog(conn).failed_since(minutes, tenant_id)


class ReminderFailureMonitor:
    """R2-01-13: alerts ops when reminder deliveries fail within the window.

    A background loop calls check() every few minutes; any FAILED delivery
    in the last 5 minutes triggers a notify_role alert (system.alert-style)
    so a dead provider channel is surfaced promptly (<= 5-min SLA).
    """

    def __init__(self, window_minutes=5):
        self.window_minutes = int(window_minutes or 5)

    async def check(self, tenant_id='default'):
        async with get_conn() as conn:
            from db.ris_message_log import MessageLog
            failed = await MessageLog(conn).failed_since(self.window_minutes, tenant_id)
            from api.notify import notify_role
            for row in failed:
                await notify_role(
                    conn, 'pacs_admin', 'reminder.delivery',
                    'Reminder delivery failed',
                    f'{row.get("channel")} to {row.get("recipient")} failed '
                    f'({row.get("attempts")} attempts) for {row.get("event_type")}.',
                    '/reminders',
                )
        return len(failed)
