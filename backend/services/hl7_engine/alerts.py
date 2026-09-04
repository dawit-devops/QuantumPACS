"""HL7 interface failure alerts (S3-17 / G5).

A FAILED message — unparseable, validation-rejected, or a processing
error — must reach an operator within minutes of the wire event. The
engine calls notify_interface_failure() on every FAILED status; the bell
fan-out targets the roles that hold HL7_READ (super_admin, tenant_admin),
honors per-user notification preferences, and throttles repeats to one
alert per user per window so a failing feed cannot flood the bell.

Bodies stay PHI-free: endpoint/facility identity and control id only, no
patient demographics or protected content.
"""

from db.notifications import Notifications
from db.notification_prefs import NotificationPrefs
from db.ris_hl7 import RisInterfaceEndpoints

ALERT_EVENT_TYPE = 'interface.failure'
ALERT_ROLE_SLUGS = ('super_admin', 'tenant_admin')
ALERT_WINDOW_MINUTES = 5
ALERT_LINK = '/admin/interfaces'


async def notify_interface_failure(conn, *, endpoint_id=None, parsed=None, error=''):
    """Fan out one throttled, pref-respecting failure alert per admin user."""
    endpoint_name = None
    if endpoint_id:
        row = await RisInterfaceEndpoints(conn).get(endpoint_id)
        endpoint_name = row['name'] if row else None

    msg_type = (parsed or {}).get('message_type', '')
    control_id = (parsed or {}).get('message_control_id', '')
    subject = f'{msg_type} {control_id}'.strip() or 'HL7 message'
    where = f' on {endpoint_name}' if endpoint_name else ''
    title = 'HL7 interface failure'
    body = f'{subject} failed{where}: {error or "unknown error"}'

    for slug in ALERT_ROLE_SLUGS:
        await _notify_role_throttled(
            conn, slug, title=title, body=body,
        )


async def _notify_role_throttled(conn, role_slug, *, title, body):
    role = await conn.fetchrow(
        'SELECT id FROM roles WHERE slug = $1', role_slug,
    )
    if not role:
        return
    rows = await conn.fetch(
        'SELECT id FROM users WHERE role_id = $1', role['id'],
    )
    for row in rows:
        user_id = row['id']
        if not await NotificationPrefs(conn).is_enabled(
            user_id, ALERT_EVENT_TYPE, role_slug=role_slug,
        ):
            continue
        if await _recent_alert_exists(conn, user_id):
            continue
        await Notifications(conn).create(
            user_id, ALERT_EVENT_TYPE, title, body, ALERT_LINK,
        )


async def _recent_alert_exists(conn, user_id) -> bool:
    return bool(await conn.fetchval(
        'SELECT EXISTS ('
        '  SELECT 1 FROM notifications'
        '  WHERE user_id = $1 AND event_type = $2 AND NOT read'
        '    AND created_at > now() - make_interval(mins => $3)'
        ')',
        user_id, ALERT_EVENT_TYPE, ALERT_WINDOW_MINUTES,
    ))
