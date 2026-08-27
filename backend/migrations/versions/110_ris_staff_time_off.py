"""RIS staff time-off requests — DM-07 staff schedule management.

Revision ID: 110
Revises: 109
Create Date: 2026-08-27

Why
---
The DM-07 staff schedule management feature (docs/ui-ux-redesign-spec.md)
needs a place to record staff time-off requests and a way to detect
coverage gaps. A staff member on approved time-off leaves a modality
under-covered on a given date; the risk is an unscheduled exam with no
available technologist. This migration creates the ris_staff_time_off
table with a status lifecycle (REQUESTED -> APPROVED/REJECTED/CANCELLED)
and a modality scope so coverage-gap detection is per-modality.

Rollback
--------
DROP TABLE ris_staff_time_off. Safe: new feature, no production data.
"""

import sqlalchemy as sa
from alembic import op

revision = '110'
down_revision = '109'
branch_labels = None
depends_on = None

TIME_OFF_STATUSES = ('REQUESTED', 'APPROVED', 'REJECTED', 'CANCELLED')


def upgrade():
    op.create_table(
        'ris_staff_time_off',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('staff_id', sa.Text(), nullable=False),
        sa.Column('staff_name', sa.Text(), server_default=''),
        sa.Column('modality', sa.Text(), server_default=''),
        sa.Column('status', sa.Text(), nullable=False,
                  server_default='REQUESTED'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), server_default=''),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name='ck_ris_staff_time_off_status',
        ),
        sa.CheckConstraint(
            'end_date >= start_date',
            name='ck_ris_staff_time_off_range',
        ),
    )
    op.create_index('ix_ris_staff_time_off_tenant_status',
                    'ris_staff_time_off', ['tenant_id', 'status'])
    op.create_index('ix_ris_staff_time_off_staff_modal',
                    'ris_staff_time_off', ['staff_id', 'modality'])


def downgrade():
    op.drop_table('ris_staff_time_off')
