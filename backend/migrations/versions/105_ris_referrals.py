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

import sqlalchemy as sa
from alembic import op

revision = '105'
down_revision = '104'
branch_labels = None
depends_on = None

STATUSES = ('pending', 'accepted', 'completed', 'cancelled')


def upgrade():
    op.create_table(
        'ris_referrals',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False,
                  server_default='default'),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('from_provider', sa.Text(), server_default=''),
        sa.Column('to_specialist', sa.Text(), nullable=False),
        sa.Column('specialty', sa.Text(), server_default=''),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('order_id', sa.Text(), server_default=''),
        sa.Column('report_id', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'completed', 'cancelled')",
            name='ck_ris_referrals_status',
        ),
    )
    op.create_index('ix_ris_referrals_patient',
                    'ris_referrals', ['patient_id'])
    op.create_index('ix_ris_referrals_tenant',
                    'ris_referrals', ['tenant_id', 'status'])


def downgrade():
    op.drop_table('ris_referrals')
