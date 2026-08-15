"""Trim legacy over-grants from tenant_admin, cashier and technologist

Revision ID: 048
Revises: 047
Create Date: 2026-08-09

Why
---
R2-14 (PACS audit 2026-08-06): the legacy unions in api/permissions.py
re-granted clinical writes the canonical matrices deliberately exclude:

- tenant_admin held PATIENT_WRITE / STUDY_WRITE / FILE_DELETE even though
  Matrix C (§5) grants "no clinical writes" — the canonical role's defining
  constraint.
- cashier held PATIENT_WRITE / STUDY_READ / FILE_READ on top of MATRIX_A_BILL,
  making it strictly more powerful than the canonical biller it mirrors.
- technologist held FILE_DELETE / PATIENT_WRITE / STUDY_WRITE beyond the
  Matrix A technologist row (exam workflow codes EXAM_* / DICOMWEB_READ are
  retained — they gate the modality worklist endpoints).

permissions.py is the single source of truth; this migration brings existing
DBs in line with the runtime seed_built_in_roles upsert so upgraded DBs do
not diverge from freshly-seeded ones (same contract as migration 046).

Schema
------
No schema change: only roles.permissions (jsonb) for the three slugs.

Rollback
--------
Restores the prior grant lists (the sets minus the removed codes).
"""

from alembic import op

revision = '048'
down_revision = '047'
branch_labels = None
depends_on = None

# Prior state — exactly what the runtime seed wrote before this change.
ROLLBACK_GRANTS = {
    'tenant_admin': [
        "AUDIT_READ", "BILLING_READ", "CDS_ADMIN", "CHART_READ", "FILE_DELETE",
        "FILE_READ", "FILE_WRITE", "INTERFACE_ADMIN", "INTERFACE_MONITOR",
        "LOG_READ", "METERING_READ", "METRICS_READ", "ORDER_READ",
        "PATIENT_READ", "PATIENT_WRITE", "REPLICA_READ", "REPLICA_WRITE",
        "REPORT_READ", "REPORT_TEMPLATE_ADMIN", "RESULTS_READ", "ROLE_DELETE",
        "ROLE_READ", "ROLE_WRITE", "SERVICE_KEY_DELETE", "SERVICE_KEY_READ",
        "SERVICE_KEY_WRITE", "STORAGE_ADMIN", "STUDY_READ", "STUDY_WRITE",
        "TENANT_ADMIN", "TENANT_READ", "USER_READ", "USER_WRITE",
        "VIEWER_READ", "WORKLIST_READ",
    ],
    'cashier': [
        "BILLING_READ", "BILLING_WRITE", "CHART_READ", "FILE_READ",
        "ORDER_READ", "PATIENT_READ", "PATIENT_WRITE", "REPORT_READ",
        "RESULTS_READ", "STUDY_READ",
    ],
    'technologist': [
        "CHART_READ", "CRITICAL_RESULTS_WRITE", "DICOMWEB_READ", "EXAM_READ",
        "EXAM_WRITE", "FILE_DELETE", "FILE_READ", "FILE_WRITE", "ORDER_READ",
        "PATIENT_READ", "PATIENT_WRITE", "RESULTS_READ", "SCHEDULE_READ",
        "STUDY_READ", "STUDY_WRITE", "VIEWER_READ", "WORKLIST_READ",
        "WORKLIST_WRITE",
    ],
}

# Canonical sets (api/permissions.py BUILT_IN_ROLES) — the trimmed grants.
UPGRADE_GRANTS = {
    'tenant_admin': [
        "AUDIT_READ", "BILLING_READ", "CDS_ADMIN", "CHART_READ", "FILE_READ",
        "FILE_WRITE", "INTERFACE_ADMIN", "INTERFACE_MONITOR", "LOG_READ",
        "METERING_READ", "METRICS_READ", "ORDER_READ", "PATIENT_READ",
        "REPLICA_READ", "REPLICA_WRITE", "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN", "RESULTS_READ", "ROLE_DELETE", "ROLE_READ",
        "ROLE_WRITE", "SERVICE_KEY_DELETE", "SERVICE_KEY_READ",
        "SERVICE_KEY_WRITE", "STORAGE_ADMIN", "STUDY_READ", "TENANT_ADMIN",
        "TENANT_READ", "USER_READ", "USER_WRITE", "VIEWER_READ",
        "WORKLIST_READ",
        # Interface surfaces (tenant_admin review P1-2): shipped to live DBs
        # by migration 061 — kept in this snapshot so the frozen record stays
        # equal to the canonical set (test_migration_048 asserts equality).
        "HL7_READ", "ROUTING_READ", "DICOMWEB_READ",
    ],
    'cashier': [
        "BILLING_READ", "BILLING_WRITE", "CHART_READ", "ORDER_READ",
        "PATIENT_READ", "REPORT_READ", "RESULTS_READ",
    ],
    'technologist': [
        "CHART_READ", "CRITICAL_RESULTS_WRITE", "DICOMWEB_READ", "EXAM_READ",
        "EXAM_WRITE", "FILE_READ", "FILE_WRITE", "ORDER_READ", "PATIENT_READ",
        "RESULTS_READ", "SCHEDULE_READ", "STUDY_READ", "VIEWER_READ",
        "WORKLIST_READ", "WORKLIST_WRITE",
    ],
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