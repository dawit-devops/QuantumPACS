"""Tenant data plane: files.size, tenants.plan, tenant_usage_daily

Revision ID: 039
Revises: 038
Create Date: 2026-08-06

Why
---
Wires the dormant DB-per-tenant data plane end to end:

- files.size (BIGINT, NOT NULL, 0) — per-file byte size backing
  Tenants.get_stats() storage accounting. Previously get_stats referenced
  files.size which did not exist (the SUM fell over at runtime).
- tenants.plan (TEXT, NOT NULL, 'free') — subscription plan slug carried
  through create/patch and the provisioning API.
- tenant_usage_daily (slug, day) — per-tenant daily metering table
  (api_calls / storage_bytes / active_users) written by the metering hook
  (db/metering.py, Stream S3) and read by metering endpoints.

Data Migration
--------------
Existing files rows get size = 0 (unknown until a storage audit runs);
existing tenants rows get plan = 'free'.

Rollback
--------
Drops the index, the metering table, and both columns.

References
----------
- ADR-010: Multi-tenant architecture
"""

from alembic import op

revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS size BIGINT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free'")
    op.execute("""
    CREATE TABLE IF NOT EXISTS tenant_usage_daily (
        slug TEXT NOT NULL,
        day DATE NOT NULL,
        api_calls BIGINT NOT NULL DEFAULT 0,
        storage_bytes BIGINT NOT NULL DEFAULT 0,
        active_users INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (slug, day)
    )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS tenant_usage_daily_slug_day "
        "ON tenant_usage_daily(slug, day)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS tenant_usage_daily_slug_day")
    op.execute("DROP TABLE IF EXISTS tenant_usage_daily")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS plan")
    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS size")
