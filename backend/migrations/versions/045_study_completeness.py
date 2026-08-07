"""Study completeness tracking (ME-05)

Revision ID: 045
Revises: 044
Create Date: 2026-08-07

Why
---
PACS audit remediation (docs/PACS_AUDIT-2026-08-06.md), ME-05:

- No study completeness tracking: instances were stored with no counter and
  no study-level status, so nothing could distinguish a partial study from
  a complete one. Add `received_instances` (maintained on every C-STORE /
  STOW insert), `expected_instances` (0 = unknown; set by integrators) and
  `study_status` (receiving/complete/incomplete).
- The ORU^R01 handler flips a matching study to `complete`; the store path
  flips it when an expected count is configured and reached.

Data Migration
--------------
Existing rows keep received_instances=0 and status 'receiving'.

Rollback
--------
Drops the columns, constraint and index.
"""

from alembic import op

revision = '045'
down_revision = '044'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS received_instances INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS expected_instances INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS study_status TEXT NOT NULL DEFAULT 'receiving'")
    op.execute("ALTER TABLE studies DROP CONSTRAINT IF EXISTS ck_studies_study_status")
    op.execute(
        "ALTER TABLE studies ADD CONSTRAINT ck_studies_study_status "
        "CHECK (study_status IN ('receiving', 'complete', 'incomplete'))",
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_studies_study_status ON studies(study_status)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_studies_study_status")
    op.execute("ALTER TABLE studies DROP CONSTRAINT IF EXISTS ck_studies_study_status")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS study_status")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS expected_instances")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS received_instances")
