"""Index the audit dashboard table by tenant

Revision ID: 056
Revises: 055
Create Date: 2026-08-12

Why
---
dashboard_audit carries a tenant column (populated from the request context,
M-6) but had no index on it. Tenant-scoped dashboard/audit readers filter by
tenant; without the index those queries scan the full table per request.

Data Migration
--------------
None — index only.

Rollback
--------
Drops the index.

References
----------
- M-6: audit rows tagged with the effective tenant
"""

from alembic import op

revision = '056'
down_revision = '055'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dashboard_audit_tenant ON dashboard_audit(tenant)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_dashboard_audit_tenant")
