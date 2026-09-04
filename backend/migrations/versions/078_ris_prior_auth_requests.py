"""RIS Prior Authorization — ris_prior_auth_requests (R2-01-01)

Revision ID: 078
Revises: 077
Create Date: 2026-08-21

Why
---
v1.1 (E-RIS2-01) adds prior-authorization tracking. ris_orders already
carries a prior_auth_status tag (schema v1) and the scheduling engine
blocks REQUIRED/PENDING/DENIED/EXPIRED orders (C-7). This migration adds
the dedicated request table that holds the payer exchange state (auth
number, approved units, expiry, denial reason) and drives that status
column. Follows the codebase tenant_id convention (no facilities table)
exactly like ris_orders / ris_charges.

Rollback
--------
Drops ris_prior_auth_requests.
"""

from alembic import op

revision = '078'
down_revision = '077'
branch_labels = None
depends_on = None

PRIOR_AUTH_STATUSES = ('NOT_REQUIRED', 'REQUIRED', 'PENDING', 'APPROVED',
                       'DENIED', 'EXPIRED')


def upgrade():
    op.execute("""
    CREATE TABLE ris_prior_auth_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        order_id UUID NOT NULL REFERENCES ris_orders(id),
        procedure_code TEXT NOT NULL DEFAULT '',
        cpt_code TEXT DEFAULT '',
        payer_id TEXT DEFAULT '',
        payer_name TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'REQUIRED'
            CHECK (status IN ('NOT_REQUIRED', 'REQUIRED', 'PENDING',
                              'APPROVED', 'DENIED', 'EXPIRED')),
        auth_number TEXT DEFAULT '',
        approved_units INTEGER,
        approved_date DATE,
        expiry_date DATE,
        denial_reason TEXT DEFAULT '',
        requested_by TEXT DEFAULT '',
        decided_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_prior_auth_tenant_status '
        'ON ris_prior_auth_requests(tenant_id, status)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_prior_auth_order '
        'ON ris_prior_auth_requests(order_id)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_prior_auth_expiry '
        'ON ris_prior_auth_requests(expiry_date) WHERE status = \'APPROVED\'')


def downgrade():
    op.drop_table('ris_prior_auth_requests')
