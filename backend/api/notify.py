"""Shared notification helpers.

Both the R06 exam lifecycle (handoff -> radiologist) and the R12 reporting
workflow (sign -> QA, peer review assignment/completion) create role-scoped and
per-user notifications. Keeping the helpers here avoids duplicating the
users/roles lookups in each module.
"""
from db.notifications import Notifications


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
    n = Notifications(conn)
    for row in rows:
        await n.create(row['id'], event_type, title, body, link)


async def notify_user(conn, user_id, event_type, title, body, link):
    """Create a notification for a single user (by id)."""
    # users.id is a bigint; compare via text cast since callers pass string ids.
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE id::text = $1", str(user_id),
    )
    if not row:
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
