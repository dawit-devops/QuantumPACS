"""Create routing_rules table for study routing

Revision ID: 020
Revises: 019
Create Date: 2026-07-26

Adds:
- routing_rules table for DICOM study routing based on metadata conditions
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS routing_rules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        conditions JSONB NOT NULL DEFAULT '{}',
        destination TEXT NOT NULL,
        priority INT NOT NULL DEFAULT 0,
        enabled BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_routing_rules_enabled ON routing_rules(enabled)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_routing_rules_priority ON routing_rules(priority)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_routing_rules_priority")
    op.execute("DROP INDEX IF EXISTS ix_routing_rules_enabled")
    op.execute("DROP TABLE IF EXISTS routing_rules")
