"""RIS waitlist table — S-08 waitlist management.

Revision ID: 103
Revises: 102
Create Date: 2026-08-26

Why
---
The RIS program (docs/ui-ux-redesign-spec.md S-08) needs a waitlist for
cancelled appointment slots. When a slot opens (cancellation), the
system matches waitlisted entries by resource + priority and notifies
the scheduler. This migration creates the ris_waitlist table.

Rollback
--------
DROP TABLE ris_waitlist. Safe: no production data (feature not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '103'
down_revision = '102'
branch_labels = None
depends_on = None

PRIORITIES = ('ROUTINE', 'URGENT', 'STAT')
WAITLIST_STATUSES = ('WAITING', 'NOTIFIED', 'BOOKED', 'EXPIRED', 'CANCELLED')


def upgrade():
    op.create_table(
        'ris_waitlist',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('resource_id', sa.Text(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('patient_name', sa.Text(), server_default=''),
        sa.Column('priority', sa.Text(), nullable=False, server_default='ROUTINE'),
        sa.Column('status', sa.Text(), nullable=False, server_default='WAITING'),
        sa.Column('modality', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.Column('notified_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "priority IN ('ROUTINE', 'URGENT', 'STAT')",
            name='ck_ris_waitlist_priority',
        ),
        sa.CheckConstraint(
            "status IN ('WAITING', 'NOTIFIED', 'BOOKED', 'EXPIRED', 'CANCELLED')",
            name='ck_ris_waitlist_status',
        ),
    )
    op.create_index('ix_ris_waitlist_tenant_resource',
                    'ris_waitlist', ['tenant_id', 'resource_id', 'status'])
    op.create_index('ix_ris_waitlist_patient',
                    'ris_waitlist', ['patient_id'])


def downgrade():
    op.drop_table('ris_waitlist')