"""Create api_keys table for service-to-service auth

Revision ID: 016
Revises: 015
Create Date: 2026-07-25

Adds:
- api_keys table with UUID PK, key_hash, prefix, service_name, permissions, expiry, etc.
"""

from alembic import op

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        prefix TEXT NOT NULL,
        service_name TEXT NOT NULL,
        permissions JSONB DEFAULT '[]',
        created_by UUID,
        expires_at TIMESTAMPTZ,
        last_used_at TIMESTAMPTZ,
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_prefix ON api_keys(prefix)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_api_keys_prefix")
    op.execute("DROP TABLE IF EXISTS api_keys")
