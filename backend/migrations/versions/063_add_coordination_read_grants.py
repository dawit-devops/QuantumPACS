"""Add coordination read grants (care_coordinator review P0-1/P1-1)

Revision ID: 063
Revises: 062
Create Date: 2026-08-14

Why
---
care_coordinator user-feature-review P0-1/P1-1 (2026-08-14):

- WORKLIST_READ (read-only) unlocks the Schedule Board's day data
  (GET /api/v2/worklist). Both care_coordinator and physician held
  SCHEDULE_READ (so the route rendered) without WORKLIST_READ (so the data
  403'd) — the same dead end R13 fixed for resident by adding WORKLIST_READ
  to MATRIX_B_RES. The board sidebar item already gates on WORKLIST_READ, so
  these roles couldn't even discover the page.
- FILE_READ (read-only) un-dead-ends the always-visible Files page for the
  same roles (route passes via STUDY_READ; the file list requires FILE_READ).
  The R13 comment already asserted physician holds FILE_READ; the matrix
  never granted it.

permissions.py MATRIX_B_PHYS / MATRIX_B_COORD are the source of truth. This
migration appends only the two missing read grants to the existing rows,
preserving facility edits to every other grant (unlike 062, which restored
whole canonical sets after over-grant drift).

Schema
------
No schema change: only roles.permissions (jsonb) for the two slugs.

Rollback
--------
No-op downgrade (grant repair is data, not a schema inversion; the prior
sets are not preserved).
"""

from alembic import op

revision = '063'
down_revision = '062'
branch_labels = None
depends_on = None

# (slug, grant) pairs added if missing. Read-only only: no WORKLIST_WRITE /
# FILE_WRITE / FILE_DELETE.
ADDITIVE_GRANTS = [
    ('care_coordinator', 'WORKLIST_READ'),
    ('care_coordinator', 'FILE_READ'),
    ('physician', 'WORKLIST_READ'),
    ('physician', 'FILE_READ'),
]


def upgrade():
    for slug, grant in ADDITIVE_GRANTS:
        op.execute(f"""
        UPDATE roles
        SET permissions = permissions || '["{grant}"]'::jsonb, updated_at = now()
        WHERE slug = '{slug}' AND built_in = TRUE
          AND NOT permissions ? '{grant}'
        """)


def downgrade():
    # Grant repair is a data change, not a schema inversion — nothing to undo.
    pass
