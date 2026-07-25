"""Add slug and default_role to oauth_providers

Revision ID: 013
Revises: 012
Create Date: 2026-07-25

Adds:
- slug column (unique, used in ?idp=<slug> URL param)
- default_role column (role slug for JIT-provisioned users)
"""

from alembic import op

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE oauth_providers
      ADD COLUMN IF NOT EXISTS slug TEXT,
      ADD COLUMN IF NOT EXISTS default_role TEXT DEFAULT 'cashier'
    """)
    op.execute("""
    UPDATE oauth_providers SET slug = 'provider-' || replace(gen_random_uuid()::text, '-', '') WHERE slug IS NULL
    """)
    op.execute("ALTER TABLE oauth_providers ALTER COLUMN slug SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_oauth_providers_slug ON oauth_providers(slug)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_oauth_providers_slug")
    op.execute("ALTER TABLE oauth_providers DROP COLUMN IF EXISTS slug")
    op.execute("ALTER TABLE oauth_providers DROP COLUMN IF EXISTS default_role")
