"""per-patient reminder opt-out

Revision ID: 096
Revises: 095
Create Date: 2026-08-25 01:30:00.000000

CS4/CC-12: per-patient reminder opt-out registry. Until now the only
opt-out was the tenant-level per-event `active` flag on ris_reminder_config;
patients had no way to decline. A NULL event_type row opts the patient out
of ALL reminder events — expressed as a unique index on
(tenant_id, patient_id, COALESCE(event_type, '')) since Postgres UNIQUE
treats NULLs as distinct.
"""

from alembic import op

revision = '096'
down_revision = '095'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS patient_reminder_optouts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            event_type TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now(),
            created_by TEXT DEFAULT ''
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_optout
        ON patient_reminder_optouts (tenant_id, patient_id,
                                     COALESCE(event_type, ''))
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_patient_optout_patient
        ON patient_reminder_optouts(patient_id)
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS patient_reminder_optouts")
