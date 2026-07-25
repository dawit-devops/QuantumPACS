"""Create tenants table for multi-tenant registry

Revision ID: 010
Revises: 009
Create Date: 2026-07-25

Adds:
- tenants table (registry database reference)
"""

from alembic import op

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        domain TEXT,
        db_name TEXT NOT NULL,
        db_host TEXT NOT NULL DEFAULT '127.0.0.1',
        db_port INTEGER NOT NULL DEFAULT 5432,
        db_user TEXT NOT NULL,
        db_password TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        storage_quota_bytes BIGINT NOT NULL DEFAULT 0,
        storage_used_bytes BIGINT NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS tenants_slug ON tenants(slug)")
    op.execute("CREATE INDEX IF NOT EXISTS tenants_domain ON tenants(domain)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
