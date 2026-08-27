"""RIS discharge planning checklists table — CC-06.

Revision ID: 106
Revises: 105
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md CC-06) needs pre-discharge
checklists (follow-up appointments, medication reconciliation, patient
education) with template-based items and per-item status. This migration
creates the ris_discharge_checklists table.

Rollback
--------
DROP TABLE ris_discharge_checklists. Safe: no production data (feature
not shipped).
"""

from alembic import op

revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None

STATUSES = ('open', 'completed')


def upgrade():
    # CREATE TABLE IF NOT EXISTS — the repo's sync_db() may have created the
    # table already on a drifted dev database; keep this idempotent.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_discharge_checklists (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            patient_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'Discharge Checklist',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'completed')),
            items JSON NOT NULL DEFAULT '[]'::json,
            notes TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_discharge_patient "
        "ON ris_discharge_checklists(patient_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_discharge_tenant "
        "ON ris_discharge_checklists(tenant_id, status)")


def downgrade():
    op.drop_table('ris_discharge_checklists')
