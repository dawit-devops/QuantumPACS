"""RIS payer contract rates (B-08) + fee schedule version history (B-09).

Revision ID: 111
Revises: 110
Create Date: 2026-08-27

Why
---
B-08 Payer Contract Rates: the billing module needs a place to record the
contracted reimbursement rate a payer agrees to pay for a given procedure.
Without it there is no way to compare actual charges against contracted
rates or flag under/over-charges — a core revenue-integrity control.

B-09 Procedure Fee Schedule: the existing procedure_pricing_catalog holds the
standard list price but has no version history, so a rate change destroys the
audit trail of who changed what and when. ris_fee_schedule_history records
every list-price edit so past rates can be reviewed and restored.

Rollback
--------
DROP TABLE ris_payer_contracts; DROP TABLE ris_fee_schedule_history.
"""

import sqlalchemy as sa
from alembic import op

revision = '111'
down_revision = '110'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ris_payer_contracts',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('payer_id', sa.Text(), nullable=False),
        sa.Column('payer_name', sa.Text(), server_default=''),
        sa.Column('procedure_code', sa.Text(), nullable=False),
        sa.Column('contracted_rate', sa.Numeric(12, 2), nullable=False),
        sa.Column('effective_date', sa.Date(), server_default=sa.text('now()')),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.CheckConstraint('contracted_rate >= 0',
                          name='ck_ris_payer_contracts_rate'),
    )
    op.create_index('ix_ris_payer_contracts_tenant',
                    'ris_payer_contracts', ['tenant_id', 'payer_id'])
    op.create_index('ix_ris_payer_contracts_proc',
                    'ris_payer_contracts', ['tenant_id', 'procedure_code'])

    op.create_table(
        'ris_fee_schedule_history',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('procedure_code', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('list_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('changed_by', sa.Text(), server_default=''),
        sa.Column('changed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_ris_fee_schedule_history_proc',
                    'ris_fee_schedule_history', ['tenant_id', 'procedure_code', 'changed_at'])


def downgrade():
    op.drop_table('ris_fee_schedule_history')
    op.drop_table('ris_payer_contracts')
