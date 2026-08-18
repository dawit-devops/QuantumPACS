"""Critical-results flag columns on exams (technologist review P1-1)

Revision ID: 065
Revises: 064
Create Date: 2026-08-17

Why
---
The technologist review's critical-results flag (CRITICAL_RESULTS_WRITE)
exists only as ALTER-style guards inside Exams.sync_db() (backend/db/exams.py)
— a runtime schema sync that container and CI boots deliberately skip
(sync_db=False). The resident reading-list query now SELECTs
critical_flag / critical_flag_note / critical_flagged_at, so any deployment
booted without sync_db 500s on /api/reports/reading-list with
UndefinedColumnError. This migration moves the columns into the normal
schema chain; the sync_db guards stay as idempotent self-healing for
long-lived dev DBs.

Rollback
--------
Drops the four columns. Safe: the flag was never durable before this
migration, and an in-flight critical flag loses nothing worse than the
pre-migration state.
"""

import sqlalchemy as sa
from alembic import op

revision = '065'
down_revision = '064'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('exams', sa.Column('critical_flag', sa.Text(), server_default=''))
    op.add_column('exams', sa.Column('critical_flag_note', sa.Text(), server_default=''))
    op.add_column('exams', sa.Column('critical_flagged_at', sa.DateTime(timezone=True)))
    op.add_column('exams', sa.Column('critical_flagged_by', sa.Text(), server_default=''))


def downgrade():
    op.drop_column('exams', 'critical_flagged_by')
    op.drop_column('exams', 'critical_flagged_at')
    op.drop_column('exams', 'critical_flag_note')
    op.drop_column('exams', 'critical_flag')
