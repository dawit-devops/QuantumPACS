"""Denial rework chain — claims auth linkage, corrections, history (v1.1 R2-S3/S4)

Revision ID: 081
Revises: 080
Create Date: 2026-08-22

Why
---
The S11-10 intake recorded a fixed DEN-001 code and left denied claims
with no path back to SUBMITTED — billers could see a denial but never
close it out. This migration gives ris_claims a prior-auth line (billing
compliance), correction state, and an append-only event history so every
rework is attributable.

Rollback
--------
Drops ris_claim_events and the added columns.
"""

from alembic import op

revision = '081'
down_revision = '080'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE ris_claims
        ADD COLUMN IF NOT EXISTS prior_auth_number TEXT DEFAULT '',
        ADD COLUMN IF NOT EXISTS correction_count INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS resubmitted_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS rework_note TEXT DEFAULT ''
    """)
    # Widen the status vocabulary: a corrected claim re-enters the cycle
    # visibly distinct from its original submission.
    op.execute("ALTER TABLE ris_claims DROP CONSTRAINT IF EXISTS ris_claims_status_check")
    op.execute("""
    ALTER TABLE ris_claims ADD CONSTRAINT ris_claims_status_check
        CHECK (status IN ('DRAFT', 'SUBMITTED', 'ACKNOWLEDGED', 'PAID',
                          'DENIED', 'RESUBMITTED'))
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_claim_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        claim_id UUID NOT NULL REFERENCES ris_claims(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        note TEXT DEFAULT '',
        actor TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_claim_events_claim '
        'ON ris_claim_events(claim_id, created_at DESC)')


def downgrade():
    op.execute('DROP TABLE IF EXISTS ris_claim_events')
    op.execute("ALTER TABLE ris_claims DROP CONSTRAINT IF EXISTS ris_claims_status_check")
    op.execute("""
    ALTER TABLE ris_claims ADD CONSTRAINT ris_claims_status_check
        CHECK (status IN ('DRAFT', 'SUBMITTED', 'ACKNOWLEDGED', 'PAID',
                          'DENIED'))
    """)
    op.execute(
        'ALTER TABLE ris_claims '
        'DROP COLUMN IF EXISTS prior_auth_number, '
        'DROP COLUMN IF EXISTS correction_count, '
        'DROP COLUMN IF EXISTS resubmitted_at, '
        'DROP COLUMN IF EXISTS rework_note')
