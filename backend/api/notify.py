"""Shared notification helpers.

Both the R06 exam lifecycle (handoff -> radiologist) and the R12 reporting
workflow (sign -> QA, peer review assignment/completion) create role-scoped and
per-user notifications. Keeping the helpers here avoids duplicating the
users/roles lookups in each module.

P1-1 (super_admin review): every fan-out consults the recipient's
notification preferences (explicit row, else role default) so the platform
admin can mute clinical noise while keeping operational alerts.
"""
from db.notifications import Notifications
from db.notification_prefs import NotificationPrefs


async def notify_role(conn, role_slug, event_type, title, body, link):
    """Create a notification for every user with the given role slug."""
    role = await conn.fetchrow(
        "SELECT id FROM roles WHERE slug = $1", role_slug,
    )
    if not role:
        return
    rows = await conn.fetch(
        "SELECT id FROM users WHERE role_id = $1", role['id'],
    )
    if not rows:
        return
    # Batch pref lookup: one query for the recipient set, then per-user
    # resolution against the shared role default.
    ids = [r['id'] for r in rows]
    pref_rows = await conn.fetch(
        "SELECT user_id, event_type, enabled FROM notification_prefs "
        "WHERE user_id = ANY($1::bigint[]) AND event_type = $2",
        ids, str(event_type),
    )
    explicit = {int(r['user_id']): bool(r['enabled']) for r in pref_rows}
    default = NotificationPrefs.default_enabled(role_slug, event_type)
    n = Notifications(conn)
    for uid in ids:
        if explicit.get(int(uid), default):
            await n.create(uid, event_type, title, body, link)


async def notify_user(conn, user_id, event_type, title, body, link, role_slug=None):
    """Create a notification for a single user (by id), honoring prefs.

    role_slug should be the recipient's role when known (request.user.role_slug)
    so the role default applies for event types without an explicit pref row.
    """
    # users.id is a bigint; compare via text cast since callers pass string ids.
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE id::text = $1", str(user_id),
    )
    if not row:
        return
    if not await NotificationPrefs(conn).is_enabled(
        row['id'], event_type, role_slug=role_slug,
    ):
        return
    await Notifications(conn).create(row['id'], event_type, title, body, link)


async def notify_patient_scoped(conn, patient_id, event_type, title, body, link):
    """Create a notification for every staff user scoped to a patient (R19).

    Fan-out is patient-scoped via patient_staff_scope (minimum necessary:
    staff only see notifications for patients they are linked to). Bodies
    must stay PHI-free — callers are responsible for that.
    """
    rows = await conn.fetch(
        "SELECT DISTINCT user_id FROM patient_staff_scope WHERE patient_id = $1",
        patient_id,
    )
    if not rows:
        return
    n = Notifications(conn)
    for row in rows:
        await n.create(row['user_id'], event_type, title, body, link)
