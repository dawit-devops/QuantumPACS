"""communication log

Revision ID: 099
Revises: 098
Create Date: 2026-08-25 03:05:00.000000

CS7/CC-04: inbound/outbound communication log. Distinct from encounters
(which are care contacts): this is the correspondence trail — who called,
what was sent, over which channel, tied to which order.
"""

from alembic import op

revision = '099'
down_revision = '098'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            direction TEXT NOT NULL
                CHECK (direction IN ('inbound', 'outbound')),
            channel TEXT NOT NULL DEFAULT 'phone',
            category TEXT DEFAULT '',
            summary TEXT NOT NULL,
            related_order_id TEXT DEFAULT '',
            logged_by TEXT DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_communications_patient_time
        ON communications(tenant_id, patient_id, created_at DESC)
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS communications")
