"""Add decommissioned_at column to tenants table

Revision ID: 015
Revises: 014
Create Date: 2026-07-25

Why
---
Adds decommissioned_at TIMESTAMPTZ to the tenants table for tenant soft-deletion
support, allowing decommissioned tenants to be restored if needed.

Data Migration
--------------
None — new column only.

Rollback
--------
Drops the decommissioned_at column.

References
----------
- ADR-010: Multi-tenant architecture
"""

from alembic import op

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS decommissioned_at TIMESTAMPTZ")


def downgrade():
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS decommissioned_at")
