"""Reading worklist assignment + priority/physician flow (ME-04)

Revision ID: 044
Revises: 043
Create Date: 2026-08-07

Why
---
PACS audit remediation (docs/PACS_AUDIT-2026-08-06.md), ME-04:

- No `assigned_radiologist` concept existed, so the reading worklist could
  never be per-physician. Add the column so a radiologist can claim/take an
  exam and filter the list to their own queue.
- `exams.referring_physician` is denormalized at adoption time from the
  source worklist entry (OBR-16, via HL7 ORM) or the exam-creation request.
  The reading worklist (which joins exams + reports only) can then filter by
  referring physician without an extra join, and `reports/reading-list`
  gains a physician filter.

Data Migration
--------------
Existing rows stay ''; the columns are additive (exams are typically created
through the adopt path which populates them going forward).

Rollback
--------
Drops the two columns and the index.
"""

from alembic import op

revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS assigned_radiologist TEXT DEFAULT ''")
    op.execute("ALTER TABLE exams ADD COLUMN IF NOT EXISTS referring_physician TEXT DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_radiologist ON exams(assigned_radiologist)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_exams_radiologist")
    op.execute("ALTER TABLE exams DROP COLUMN IF EXISTS assigned_radiologist")
    op.execute("ALTER TABLE exams DROP COLUMN IF EXISTS referring_physician")
