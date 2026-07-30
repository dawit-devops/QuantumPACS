"""Add tenant, request_id, trace_id columns to logs table

Revision ID: 014
Revises: 013
Create Date: 2026-07-25

Why
---
Adds tenant, request_id, and trace_id columns to the logs table for multi-tenant
audit trail isolation and distributed-tracing correlation across services.

Data Migration
--------------
None — new columns only.

Rollback
--------
Drops indexes and columns.

References
----------
- ADR-010: Multi-tenant architecture
- ADR-014: Distributed tracing design
"""

from alembic import op

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE logs ADD COLUMN IF NOT EXISTS tenant TEXT")
    op.execute("ALTER TABLE logs ADD COLUMN IF NOT EXISTS request_id TEXT")
    op.execute("ALTER TABLE logs ADD COLUMN IF NOT EXISTS trace_id TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_logs_tenant ON logs(tenant)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_logs_request_id ON logs(request_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_logs_request_id")
    op.execute("DROP INDEX IF EXISTS ix_logs_tenant")
    op.execute("ALTER TABLE logs DROP COLUMN IF EXISTS trace_id")
    op.execute("ALTER TABLE logs DROP COLUMN IF EXISTS request_id")
    op.execute("ALTER TABLE logs DROP COLUMN IF EXISTS tenant")
