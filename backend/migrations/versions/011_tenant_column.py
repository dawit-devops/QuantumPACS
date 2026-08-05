"""Add tenant column to users table for tenant-scoped JWT

Revision ID: 011
Revises: 010
Create Date: 2026-07-25

Why
---
Adds users.tenant column for tenant-scoped JWT tokens, enabling the authentication
backend to restrict user access to their assigned tenant's data.

Data Migration
--------------
None — new column only.

Rollback
--------
Drops index and column.

References
----------
- ADR-010: Multi-tenant architecture
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
