"""Reconcile drifted built-in role grants (technologist, radiologist, resident, cashier)

Revision ID: 062
Revises: 061
Create Date: 2026-08-14

Why
---
technologist user-feature-review P0-1 (2026-08-14): the dev DB's
`technologist` (92 vs canonical 15), `radiologist` (92 vs 23), `resident`
(27 vs 18) and `cashier` (8 vs 7) built-in role rows carry stale grants —
login tokens are minted from the DB role row (`db/users.get_user_role`), so
the app grants far more than `BUILT_IN_ROLES`. Migration 048 trimmed these
slugs on 2026-08-09, but the rows were overwritten afterwards (role
`updated_at` 08-12/13), re-introducing the over-grants.

permissions.py is the single source of truth; this migration re-applies the
canonical sets to the drifted slugs so upgraded DBs converge with
freshly-seeded ones (same contract as migrations 046/048).

Schema
------
No schema change: only roles.permissions (jsonb) for the four slugs.

Rollback
--------
No-op downgrade (grant drift is data repair, not a schema inversion; the
prior over-granted sets are not preserved).
"""

from alembic import op

revision = '062'
down_revision = '061'
branch_labels = None
depends_on = None

# Canonical grants (api/permissions.py BUILT_IN_ROLES) for the drifted slugs.
CANONICAL_GRANTS = {
    'technologist': [
        "CHART_READ", "CRITICAL_RESULTS_WRITE", "DICOMWEB_READ", "EXAM_READ",
        "EXAM_WRITE", "FILE_READ", "FILE_WRITE", "ORDER_READ", "PATIENT_READ",
        "RESULTS_READ", "SCHEDULE_READ", "STUDY_READ", "VIEWER_READ",
        "WORKLIST_READ", "WORKLIST_WRITE",
    ],
    'radiologist': [
        "PATIENT_READ", "ORDER_READ", "SCHEDULE_READ", "PRIOR_AUTH_READ",
        "WORKLIST_READ", "WORKLIST_WRITE", "REPORT_READ", "REPORT_WRITE",
        "REPORT_SIGN", "CRITICAL_RESULTS_WRITE", "REPORT_TEMPLATE_ADMIN",
        "VIEWER_READ", "STUDY_READ", "STUDY_EXPORT", "CHART_READ",
        "RESULTS_READ", "MED_ORDER_READ", "CROSS_TENANT_READ", "FILE_READ",
        "EXAM_READ", "PEER_REVIEW_READ", "PEER_REVIEW_WRITE", "DICOMWEB_READ",
    ],
    'resident': [
        "CHART_READ", "PATIENT_READ", "ENCOUNTER_WRITE", "MED_ORDER_READ",
        "MED_ORDER_WRITE", "MAR_READ", "ORDER_READ", "ORDER_WRITE",
        "RESULTS_READ", "SCHEDULE_READ", "PRIOR_AUTH_READ", "REPORT_READ",
        "STUDY_READ", "VIEWER_READ", "CARE_PLAN_WRITE", "REPORT_WRITE",
        "FILE_READ", "WORKLIST_READ",
    ],
    'cashier': [
        "BILLING_READ", "BILLING_WRITE", "CHART_READ", "ORDER_READ",
        "PATIENT_READ", "REPORT_READ", "RESULTS_READ",
    ],
}


def _update(slug, grants):
    perms_json = ", ".join(f"\"{p}\"" for p in grants)
    op.execute(f"""
    UPDATE roles SET permissions = '[{perms_json}]'::jsonb, updated_at = now()
    WHERE slug = '{slug}' AND built_in = TRUE
    """)


def upgrade():
    for slug, grants in CANONICAL_GRANTS.items():
        _update(slug, grants)


def downgrade():
    # Grant drift is a data repair, not a schema inversion — nothing to undo.
    pass
