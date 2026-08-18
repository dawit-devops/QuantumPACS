"""Grant HL7_READ, ROUTING_READ, DICOMWEB_READ to the tenant_admin built-in role

Revision ID: 061
Revises: 060
Create Date: 2026-08-14

Why
---
tenant_admin review (C2): the facility operator held INTERFACE_ADMIN /
INTERFACE_MONITOR / STORAGE_ADMIN but none of those grants unlocked a
reachable surface — the HL7, routing and DICOMweb consoles are gated on
HL7_READ / ROUTING_READ / DICOMWEB_READ, which the role lacked, so every
dashboard "Open" button dead-ended back to /admin. The canonical set in
backend/api/permissions.py (MATRIX_C_TENANT_ADMIN) now adds the three read
grants; this migration ships them to the database because role permissions
are seeded once and only drift-corrected by explicit migrations (same
pattern as 059 for the resident).

Schema
------
No table changes. Adds HL7_READ, ROUTING_READ, DICOMWEB_READ to the built-in
tenant_admin role's permissions jsonb (idempotent append), then bumps
token_version for users holding the role so their JWTs (which embed
permissions at login) are invalidated and re-auth picks up the set.

Rollback
--------
Removes the three grants from the tenant_admin role and bumps token_version
again. (API routes stay gated on the same permissions, so removal restores
the prior dead-grant state; the review's P1-2 decision is documented in the
RBAC matrix spec.)
"""

import json

from alembic import op
from sqlalchemy import text

revision = '061'
down_revision = '060'
branch_labels = None
depends_on = None

GRANTS = ('HL7_READ', 'ROUTING_READ', 'DICOMWEB_READ')


def _tenant_admin_roles(conn):
    return conn.execute(
        text("SELECT id, permissions FROM roles WHERE slug = 'tenant_admin'")
    ).fetchall()


def _patch(conn, add):
    changed = False
    for role_id, permissions in _tenant_admin_roles(conn):
        perms = json.loads(permissions) if isinstance(permissions, str) else list(permissions or [])
        new_perms = list(perms)
        for grant in GRANTS:
            if add and grant not in new_perms:
                new_perms.append(grant)
            elif not add and grant in new_perms:
                new_perms.remove(grant)
        if new_perms != perms:
            conn.execute(
                text(
                    "UPDATE roles SET permissions = :permissions, updated_at = now() WHERE id = :role_id"
                ),
                {'permissions': json.dumps(new_perms), 'role_id': role_id},
            )
            changed = True
    return changed


def _bump_token_version(conn):
    conn.execute(
        text(
            """
            UPDATE users
            SET token_version = token_version + 1
            WHERE role_id IN (SELECT id FROM roles WHERE slug = 'tenant_admin')
            """
        )
    )


def upgrade():
    conn = op.get_bind()
    if _patch(conn, add=True):
        _bump_token_version(conn)


def downgrade():
    conn = op.get_bind()
    if _patch(conn, add=False):
        _bump_token_version(conn)
