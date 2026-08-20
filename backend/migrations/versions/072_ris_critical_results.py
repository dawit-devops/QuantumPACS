"""RIS Critical Results — schema for Sprint S10 (S10-01)

Revision ID: 072
Revises: 071
Create Date: 2026-08-20

Why
---
Sprint S10 implements critical result flagging, recipient notification (including
ED physician), acknowledgment tracking, and escalation policy background checks.

Rollback
--------
Drops ris_critical_results table.
"""

from alembic import op

revision = '072'
down_revision = '071'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_critical_results (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID,
        exam_id UUID,
        accession_number TEXT NOT NULL DEFAULT '',
        patient_id TEXT NOT NULL DEFAULT '',
        patient_name TEXT DEFAULT '',
        finding_description TEXT NOT NULL DEFAULT '',
        recipient_id TEXT DEFAULT '',
        recipient_name TEXT DEFAULT '',
        recipient_role TEXT DEFAULT 'ed_physician',
        status TEXT NOT NULL DEFAULT 'flagged'
            CHECK (status IN ('flagged', 'acknowledged', 'escalated', 'cleared')),
        flagged_by TEXT DEFAULT '',
        flagged_at TIMESTAMPTZ DEFAULT now(),
        acknowledged_by TEXT DEFAULT '',
        acknowledged_at TIMESTAMPTZ,
        escalated_at TIMESTAMPTZ,
        escalated_to TEXT DEFAULT '',
        tenant_id TEXT DEFAULT 'default',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_critical_status ON ris_critical_results(status)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_critical_accession ON ris_critical_results(accession_number)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_critical_tenant ON ris_critical_results(tenant_id)
    """)


def downgrade():
    op.drop_table('ris_critical_results')
