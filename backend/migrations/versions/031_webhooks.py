"""Create webhooks table

Revision ID: 031
Revises: 030
Create Date: 2026-07-29

Adds webhook infrastructure for outbound event notifications.
"""

from alembic import op

revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS webhooks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        events TEXT[] NOT NULL DEFAULT '{}',
        secret TEXT DEFAULT '',
        active BOOLEAN NOT NULL DEFAULT TRUE,
        retry_count INTEGER NOT NULL DEFAULT 3,
        timeout_ms INTEGER NOT NULL DEFAULT 5000,
        last_triggered_at TIMESTAMPTZ,
        last_status_code INTEGER,
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS webhooks CASCADE")
