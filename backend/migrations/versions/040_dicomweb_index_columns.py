"""DICOMweb index columns: files.sop_class_uid, files.instance_number, studies.study_date

Revision ID: 040
Revises: 039
Create Date: 2026-08-06

Why
---
DICOMweb QIDO-RS instance responses require SOPClassUID (0008,0016) and
InstanceNumber (0020,0013) as first-class fields, and study search supports
StudyDate (0008,0020) ranges. These were previously read from the files.meta
JSONB blob, which is keyed by element *name* (not keyword) and stores UID
*names* (not raw UIDs) for UI elements — so the fields were always empty.

- files.sop_class_uid (TEXT, nullable) — raw SOP Class UID, populated by
  dcm/file.get_meta() at ingest (both HTTP upload and C-STORE paths).
- files.instance_number (TEXT, nullable) — raw Instance Number string.
- studies.study_date (TEXT, nullable) — raw StudyDate YYYYMMDD, enabling
  range filters on study-level QIDO.

Data Migration
--------------
Existing rows stay NULL; a re-ingest/re-sync fills them. Backfill from meta
is skipped deliberately because the name-keyed values are not reliably the
raw UIDs.

Rollback
--------
Drops the three columns.
"""

from alembic import op

revision = '040'
down_revision = '039'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS sop_class_uid TEXT")
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS instance_number TEXT")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS study_date TEXT")


def downgrade():
    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS sop_class_uid")
    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS instance_number")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS study_date")
