"""Create api_keys table for service-to-service auth

Revision ID: 016
Revises: 015
Create Date: 2026-07-25

Why
---
Creates the api_keys table for service-to-service authentication, storing
hashed API keys with granular permission sets and optional expiry dates
for machine-to-machine communication.

Data Migration
--------------
None — new table only.

Rollback
--------
Drops the api_keys table and its prefix index.

References
----------
- ADR-016: Service-to-service API key auth
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
