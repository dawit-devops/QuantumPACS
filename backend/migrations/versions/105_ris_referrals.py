"""RIS referral tracking table — CC-05 referrals.

Revision ID: 105
Revises: 104
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md CC-05) needs referral
tracking from ordering provider to specialist with a pending -> accepted
-> completed (or cancelled) lifecycle, optionally linked to an order and
a follow-up report. This migration creates the ris_referrals table.

Rollback
--------
DROP TABLE ris_referrals. Safe: no production data (feature not shipped).
"""

from alembic import op

revision = '105'
down_revision = '104'
branch_labels = None
depends_on = None

STATUSES = ('pending', 'accepted', 'completed', 'cancelled')


def upgrade():
    # CREATE TABLE IF NOT EXISTS — the repo's sync_db() may have created the
    # table already on a drifted dev database; keep this idempotent.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_referrals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            patient_id TEXT NOT NULL,
            from_provider TEXT DEFAULT '',
            to_specialist TEXT NOT NULL,
            specialty TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'completed', 'cancelled')),
            order_id TEXT DEFAULT '',
            report_id TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_referrals_patient "
        "ON ris_referrals(patient_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_referrals_tenant "
        "ON ris_referrals(tenant_id, status)")


def downgrade():
    op.drop_table('ris_referrals')
