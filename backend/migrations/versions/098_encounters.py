"""encounters

Revision ID: 098
Revises: 097
Create Date: 2026-08-25 02:40:00.000000

CS6/CC-03: patient encounter log for the care coordinator. ENCOUNTER_WRITE
was pre-granted but gated nothing; this gives it a surface. Rows are
patient-scoped contact records (visit/call/message/fax) optionally linked
to an order or report.
"""

from alembic import op

revision = '098'
down_revision = '097'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS encounters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            encounter_type TEXT NOT NULL
                CHECK (encounter_type IN ('visit', 'call', 'message', 'fax')),
            occurred_at TIMESTAMPTZ DEFAULT now(),
            summary TEXT NOT NULL,
            linked_order_id TEXT DEFAULT '',
            linked_report_id TEXT DEFAULT '',
            recorded_by TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_encounters_patient_time
        ON encounters(tenant_id, patient_id, occurred_at DESC)
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS encounters")
