"""Worklist in_progress status for partial-study tracking

Revision ID: 042
Revises: 041
Create Date: 2026-08-06

Why
---
PACS audit ME-05: match_worklist_performed fired on the first stored
instance, so a partial study marked the MWL entry performed. Study
completeness is signalled by the ORU^R01 result message, not by the
first C-STORE. Add an `in_progress` status so a store transitions
scheduled -> in_progress, and only ORU (results reported) marks the
entry performed.

Rollback
--------
Restores the previous CHECK constraint; rows already in_progress are
reset to scheduled.
"""

from alembic import op

revision = '042'
down_revision = '041'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE worklist_entries DROP CONSTRAINT IF EXISTS worklist_entries_status_check"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD CONSTRAINT worklist_entries_status_check "
        "CHECK (status IN ('scheduled', 'in_progress', 'performed', 'cancelled'))"
    )


def downgrade():
    op.execute(
        "ALTER TABLE worklist_entries DROP CONSTRAINT IF EXISTS worklist_entries_status_check"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD CONSTRAINT worklist_entries_status_check "
        "CHECK (status IN ('scheduled', 'performed', 'cancelled'))"
    )
