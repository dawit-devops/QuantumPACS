"""Add tenant_id column to routing_rules

Revision ID: 021
Revises: 020
Create Date: 2026-07-26

Why
---
Adds tenant_id column to routing_rules for tenant-scoped routing rules, so
each tenant can define independent study distribution policies.

Data Migration
--------------
None — new column only.

Rollback
--------
Drops index and column.

References
----------
- ADR-010: Multi-tenant architecture
- ADR-020: DICOM study routing
"""

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE routing_rules ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS ix_routing_rules_tenant_id ON routing_rules(tenant_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_routing_rules_tenant_id")
    op.execute("ALTER TABLE routing_rules DROP COLUMN IF EXISTS tenant_id")
