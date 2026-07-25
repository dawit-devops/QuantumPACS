"""Add tenant column to users table for tenant-scoped JWT

Revision ID: 011
Revises: 010
Create Date: 2026-07-25

Adds:
- users.tenant TEXT — which tenant this user belongs to
"""

from alembic import op

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS users_tenant ON users(tenant)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS users_tenant")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS tenant")
