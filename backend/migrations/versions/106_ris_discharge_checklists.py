"""RIS discharge planning checklists table — CC-06.

Revision ID: 106
Revises: 105
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md CC-06) needs pre-discharge
checklists (follow-up appointments, medication reconciliation, patient
education) with template-based items and per-item status. This migration
creates the ris_discharge_checklists table.

Rollback
--------
DROP TABLE ris_discharge_checklists. Safe: no production data (feature
not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None

STATUSES = ('open', 'completed')


def upgrade():
    op.create_table(
        'ris_discharge_checklists',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False,
                  server_default='default'),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False,
                  server_default='Discharge Checklist'),
        sa.Column('status', sa.Text(), nullable=False, server_default='open'),
        sa.Column('items', sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'::json")),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.CheckConstraint(
            "status IN ('open', 'completed')",
            name='ck_ris_discharge_checklists_status',
        ),
    )
    op.create_index('ix_ris_discharge_patient',
                    'ris_discharge_checklists', ['patient_id'])
    op.create_index('ix_ris_discharge_tenant',
                    'ris_discharge_checklists', ['tenant_id', 'status'])


def downgrade():
    op.drop_table('ris_discharge_checklists')
