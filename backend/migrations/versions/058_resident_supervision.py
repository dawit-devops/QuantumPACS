"""R13 resident supervision: submit/co-sign/return columns + status

Revision ID: 058
Revises: 057
Create Date: 2026-08-14

Why
---
The R13 supervised-reading loop needs a resident to hand a draft to the
supervising attending (submit), for the attending to either co-sign it into
final (existing REPORT_SIGN) or return it for revision with feedback. The
reports.status CHECK only allowed draft/preliminary/final; this migration
adds the 'submitted' state plus the review columns that carry the loop's
metadata (submitted_at, review_feedback, reviewed_by, reviewed_at).

Rollback
--------
Restores the three-state CHECK and drops the four review columns.

References
----------
- docs/requirements/resident/10-resident-ui-ux-design.md (B3)
"""

import sqlalchemy as sa
from alembic import op

revision = '058'
down_revision = '057'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reports', sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('reports', sa.Column('review_feedback', sa.Text(), nullable=False, server_default=''))
    op.add_column('reports', sa.Column('reviewed_by', sa.Text(), nullable=False, server_default=''))
    op.add_column('reports', sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True))
    # Extend the status CHECK to admit the submitted (awaiting co-sign) state.
    op.execute(
        "ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_status_check"
    )
    op.create_check_constraint(
        'reports_status_check',
        'reports',
        "status IN ('draft', 'preliminary', 'submitted', 'final')",
    )


def downgrade():
    op.execute(
        "ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_status_check"
    )
    op.create_check_constraint(
        'reports_status_check',
        'reports',
        "status IN ('draft', 'preliminary', 'final')",
    )
    op.drop_column('reports', 'reviewed_at')
    op.drop_column('reports', 'reviewed_by')
    op.drop_column('reports', 'review_feedback')
    op.drop_column('reports', 'submitted_at')
