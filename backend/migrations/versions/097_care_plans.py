"""care plans

Revision ID: 097
Revises: 096
Create Date: 2026-08-25 02:10:00.000000

CS5/CC-02: care plan records for the care coordinator. CARE_PLAN_WRITE was
pre-granted but gated nothing; this gives it a surface. Tasks are a JSONB
array of {label, done} to keep the schema flat; status is a CHECK.
"""

from alembic import op

revision = '097'
down_revision = '096'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS care_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'completed', 'on_hold')),
            tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
            responsible_provider TEXT DEFAULT '',
            follow_up_at TIMESTAMPTZ,
            notes TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_care_plans_patient
        ON care_plans(patient_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_care_plans_status
        ON care_plans(tenant_id, status)
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS care_plans")
