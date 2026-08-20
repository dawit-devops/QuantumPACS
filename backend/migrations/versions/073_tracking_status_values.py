"""Tracking status values arrived/completed

Revision ID: 073
Revises: 072
Create Date: 2026-08-20

Why
---
CR-1 (S6-15): TRACKING_VALID_TRANSITIONS in api/worklist.py permits
`arrived` and `completed`, but the worklist_entries CHECK constraint only
allowed ('scheduled', 'in_progress', 'performed', 'cancelled'). Every
manual check-in / completion update therefore failed with
CheckViolationError -> 500. Extend the constraint so the manual tracking
states (arrived, completed) coexist with the MPPS-driven state
(performed) and the C-STORE partial-study state (in_progress).

Rollback
--------
Restores the previous four-value constraint; rows already in the new
states are reset to scheduled.
"""

from alembic import op

revision = '073'
down_revision = '072'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE worklist_entries DROP CONSTRAINT IF EXISTS worklist_entries_status_check"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD CONSTRAINT worklist_entries_status_check "
        "CHECK (status IN ('scheduled', 'arrived', 'in_progress', 'performed', "
        "'completed', 'cancelled'))"
    )


def downgrade():
    op.execute(
        "UPDATE worklist_entries SET status = 'scheduled' "
        "WHERE status IN ('arrived', 'completed')"
    )
    op.execute(
        "ALTER TABLE worklist_entries DROP CONSTRAINT IF EXISTS worklist_entries_status_check"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD CONSTRAINT worklist_entries_status_check "
        "CHECK (status IN ('scheduled', 'in_progress', 'performed', 'cancelled'))"
    )
