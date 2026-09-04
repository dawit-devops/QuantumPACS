"""add assigned_technologist to worklist_entries

Revision ID: 112
Revises: 111
Create Date: 2026-08-27

Why
---
The DM-07 staff-schedule handlers (DeptStaffScheduleHandler and
StaffCoverageGapsHandler in api/ris_dashboard.py) read and write
worklist_entries.assigned_technologist, but that column only ever existed on
the exams table — no migration ever added it to worklist_entries. Any live
staff-schedule query (list/create) or coverage-gap detection raised
UndefinedColumnError. This adds the column + an index to match the exams
table, keeping the DM-07 feature functional.

Rollback
--------
DROP COLUMN assigned_technologist. Safe: additive, feature just shipped.
"""

import sqlalchemy as sa
from alembic import op

revision = '112'
down_revision = '111'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'worklist_entries',
        sa.Column('assigned_technologist', sa.Text(), nullable=False,
                  server_default=''),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_worklist_technologist "
        "ON worklist_entries(assigned_technologist)"
    )


def downgrade():
    op.drop_column('worklist_entries', 'assigned_technologist')
