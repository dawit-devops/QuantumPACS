"""Add R08 front-desk grants to canonical scheduler + receptionist roles

Revision ID: 046
Revises: 045
Create Date: 2026-08-08

Why
---
The R08 Front Desk backend (api/frontdesk.py) guards registration, visits,
order intake and the waiting queue on REGISTRATION_READ / REGISTRATION_WRITE
/ QUEUE_READ, but the canonical scheduler and receptionist roles (Matrix A,
docs/reaserch/RBAC_matrix_spec.md §5) lacked those grants — only the legacy
front_desk role carried them. The new front-desk UI (Front Desk workspace)
would 403 for those roles. This migration refreshes the two seeded rows to
match the updated MATRIX_A_SCHED / MATRIX_A_RECEPT sets in
api/permissions.py (which the runtime seed_built_in_roles upsert mirrors).

Schema
------
No schema change: only roles.permissions (jsonb) for the two slugs.

Rollback
--------
Restores the prior grant lists (grants minus the three front-desk codes).
"""

from alembic import op

revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None

# Prior state (migration 038) — the same codes permissions.py granted before
# this change, kept here verbatim so downgrade restores byte-identical lists.
ROLLBACK_GRANTS = {
    'scheduler': [
        "ORDER_READ", "PATIENT_READ", "PATIENT_WRITE", "PRIOR_AUTH_READ",
        "PRIOR_AUTH_WRITE", "SCHEDULE_READ", "SCHEDULE_WRITE", "WORKLIST_READ",
    ],
    'receptionist': [
        "ORDER_READ", "PATIENT_READ", "PATIENT_WRITE", "SCHEDULE_READ",
        "WORKLIST_READ",
    ],
}

# Canonical Matrix A sets (api/permissions.py) + the R08 grants added here.
UPGRADE_GRANTS = {
    'scheduler': sorted(set(ROLLBACK_GRANTS['scheduler']) | {
        'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ',
    }),
    'receptionist': sorted(set(ROLLBACK_GRANTS['receptionist']) | {
        'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ', 'SCHEDULE_WRITE',
    }),
}


def _update(slug, grants):
    perms_json = ", ".join(f"\"{p}\"" for p in grants)
    op.execute(f"""
    UPDATE roles SET permissions = '[{perms_json}]'::jsonb, updated_at = now()
    WHERE slug = '{slug}' AND built_in = TRUE
    """)


def upgrade():
    for slug, grants in UPGRADE_GRANTS.items():
        _update(slug, grants)


def downgrade():
    for slug, grants in ROLLBACK_GRANTS.items():
        _update(slug, grants)
