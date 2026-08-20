"""RIS worklist columns (S6-06)

Revision ID: 075
Revises: 074
Create Date: 2026-08-20

Why
---
S6-06: worklist_entries lacked the RIS linkage columns the tracking board,
MPPS consumer and booking flow need:

- ris_order_id: the ris_orders row this entry was created for (bookings are
  order-backed; order-less bookings never reach the worklist).
- mpps_status: the last modality-reported PerformedProcedureStepStatus
  (N-CREATE/N-SET), so the tracking board can distinguish modality progress
  from internal status transitions.
- body_part / contrast: MWL fields modalities expect on C-FIND (populated
  from ORM/order data).

All columns are additive; existing rows keep NULL/''/false defaults.

Rollback
--------
Drops the four columns.
"""

from alembic import op

revision = '075'
down_revision = '074'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE worklist_entries '
        'ADD COLUMN IF NOT EXISTS ris_order_id uuid '
        'REFERENCES ris_orders(id)'
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS mpps_status "
        "varchar(20) CHECK (mpps_status IN "
        "('IN_PROGRESS','COMPLETED','DISCONTINUED'))"
    )
    op.execute(
        'ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS '
        'body_part varchar(100)'
    )
    op.execute(
        'ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS '
        'contrast boolean DEFAULT false'
    )


def downgrade():
    op.execute('ALTER TABLE worklist_entries DROP COLUMN IF EXISTS contrast')
    op.execute('ALTER TABLE worklist_entries DROP COLUMN IF EXISTS body_part')
    op.execute('ALTER TABLE worklist_entries DROP COLUMN IF EXISTS mpps_status')
    op.execute('ALTER TABLE worklist_entries DROP COLUMN IF EXISTS ris_order_id')