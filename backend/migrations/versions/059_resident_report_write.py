"""Grant REPORT_WRITE and FILE_READ to the resident built-in role (R13 fix)

Revision ID: 059
Revises: 058
Create Date: 2026-08-14

Why
---
R13 (resident supervised reading, 491e279) updated the canonical resident
permission set in backend/api/permissions.py (MATRIX_B_RES gains
REPORT_WRITE so trainees can claim exams, autosave drafts and submit for
supervision), but no migration shipped the grants to the database. Role
permissions are seeded by 038_rbac_canonical_roles and only drift-corrected
by explicit migrations — there is no runtime sync, so every install kept the
resident role effectively read-only (REPORT_READ only).

Two gaps surfaced interactively in the dev stack:
- Missing REPORT_WRITE: the reading console showed "Read-only report —
  editing requires the REPORT_WRITE permission" to the assigned resident,
  blocking claim/autosave/submit.
- Missing FILE_READ: the Cornerstone viewport fetches DICOM pixels from
  /api/files/{id}, which is gated on FILE_READ. Every viewer role
  (radiologist, technologist, physician, teleradiologist) holds FILE_READ;
  without it the resident's viewport rendered the study tree but 403'd on
  pixel load ("Missing permission: FILE_READ"). FILE_READ also gates the
  notification bell endpoint, so residents were blind to their supervisor's
  return/co-sign notifications.

Schema
------
No table changes. Adds REPORT_WRITE and FILE_READ to the built-in resident
role's permissions jsonb (idempotent — only appends if absent, so re-runs
and already-patched databases are no-ops), then bumps token_version for all
users holding the resident role so their JWTs (which embed permissions at
login) are invalidated and re-auth picks up the corrected set.

Rollback
--------
Removes REPORT_WRITE and FILE_READ from the resident role and bumps
token_version again so the removal takes effect on the next login. Users
that meanwhile created drafts keep those rows (report state is not rewound).
"""

import json

from alembic import op
from sqlalchemy import text

revision = '059'
down_revision = '058'
branch_labels = None
depends_on = None

GRANTS = ('REPORT_WRITE', 'FILE_READ')


def _resident_roles(conn):
    return conn.execute(
        text("SELECT id, permissions FROM roles WHERE slug = 'resident'")
    ).fetchall()


def _patch(conn, add):
    changed = False
    for role_id, permissions in _resident_roles(conn):
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
            WHERE role_id IN (SELECT id FROM roles WHERE slug = 'resident')
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