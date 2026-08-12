"""Scope webhook subscriptions per tenant

Revision ID: 054
Revises: 053
Create Date: 2026-08-12

Why
---
Webhook subscriptions are global platform config, but once event dispatch is
built a single subscription would receive PHI-bearing events from every tenant
(M-7). Tagging each subscription with the tenant that owns it lets dispatch and
the management API scope deliveries to the subscribing tenant only.

Data Migration
--------------
None — new nullable column, backfilled to '' (platform/global) for existing rows.

Rollback
--------
Drops the tenant column.

References
----------
- M-7: PHI egress (webhooks/exports) must be tenant-scoped
"""

from alembic import op

revision = '054'
down_revision = '053'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS tenant TEXT NOT NULL DEFAULT ''")


def downgrade():
    op.execute("ALTER TABLE webhooks DROP COLUMN IF EXISTS tenant")
