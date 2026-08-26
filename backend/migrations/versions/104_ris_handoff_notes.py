"""RIS handoff notes table — CC-08 coordinator handoff notes.

Revision ID: 104
Revises: 103
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md CC-08) needs coordinator
handoff notes on patients — visible to the next coordinator, with
priority flags (low/normal/high/urgent) and read/unread tracking.
This table is intentionally named ris_handoff_notes (not handoff_notes,
which is a legacy nursing table with a different shape).

Rollback
--------
DROP TABLE ris_handoff_notes. Safe: no production data (feature not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '104'
down_revision = '103'
branch_labels = None
depends_on = None

PRIORITIES = ('low', 'normal', 'high', 'urgent')


def upgrade():
    op.create_table(
        'ris_handoff_notes',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False,
                  server_default='default'),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False, server_default=''),
        sa.Column('priority', sa.Text(), nullable=False,
                  server_default='normal'),
        sa.Column('is_read', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name='ck_ris_handoff_notes_priority',
        ),
    )
    op.create_index('ix_ris_handoff_notes_patient',
                    'ris_handoff_notes', ['patient_id'])
    op.create_index('ix_ris_handoff_notes_tenant',
                    'ris_handoff_notes', ['tenant_id', sa.text('created_at DESC')])


def downgrade():
    op.drop_table('ris_handoff_notes')
