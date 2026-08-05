"""Add slug and default_role to oauth_providers

Revision ID: 013
Revises: 012
Create Date: 2026-07-25

Why
---
Adds slug (for ?idp=<slug> URL parameter) and default_role (for JIT-provisioned
user role assignment) columns to oauth_providers for multi-provider routing.

Data Migration
--------------
Existing rows without a slug get a generated UUID-based slug; column is then
set NOT NULL.

Rollback
--------
Drops the slug unique index and both columns.

References
----------
- ADR-013: OAuth provider multi-IDP routing
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
