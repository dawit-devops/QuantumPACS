"""RIS usage counters on tenant_usage_daily (S2-02 refined)

Revision ID: 080
Revises: 079
Create Date: 2026-08-21

Why
---
TenantMiddleware already meters every tenant-scoped HTTP request as
api_calls, so /ris/* routes inherit that for free on the merged platform.
The two RIS activity surfaces that BYPASS the HTTP middleware are DICOM
MWL C-FINDs (pynetdicom, no Request object) and bell notifications
(fan-out helpers write rows without a counter). This migration adds the
two per-day counters to the shared usage table so the invoice view shows
RIS activity without a parallel metering system.

Rollback
--------
Drops both columns.
"""

from alembic import op

revision = '080'
down_revision = '079'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE tenant_usage_daily '
        'ADD COLUMN IF NOT EXISTS mwl_queries INTEGER NOT NULL DEFAULT 0')
    op.execute(
        'ALTER TABLE tenant_usage_daily '
        'ADD COLUMN IF NOT EXISTS notifications INTEGER NOT NULL DEFAULT 0')


def downgrade():
    op.execute(
        'ALTER TABLE tenant_usage_daily DROP COLUMN IF EXISTS mwl_queries')
    op.execute(
        'ALTER TABLE tenant_usage_daily DROP COLUMN IF EXISTS notifications')
