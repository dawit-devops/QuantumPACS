"""Scope API keys per tenant

Revision ID: 055
Revises: 054
Create Date: 2026-08-12

Why
---
api_keys is a global registry table in the main DB (H-1 binds a key to the
tenant its requests are scoped to). The management API previously listed and
revoked keys via the caller's tenant-routed connection (get_conn()), which for a
`default`-tenant user returned every tenant's keys and errored for separate-DB
tenants. The handlers now query the main registry DB and scope reads/writes by
the caller's effective tenant (H-3). This migration guarantees the column exists
for fresh installs; runtime sync_db also adds it defensively.

Data Migration
--------------
None — new nullable column, backfilled to '' (unscoped/platform) for existing rows.

Rollback
--------
Drops the tenant column.

References
----------
- H-1: API keys bound to a tenant
- H-3: tenant-scoped registry reads (api_keys leakage for default tenant)
"""

from alembic import op

revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tenant TEXT NOT NULL DEFAULT ''")


def downgrade():
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS tenant")
