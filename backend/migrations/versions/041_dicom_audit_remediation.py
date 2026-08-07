"""DICOM audit remediation: physician columns + worklist MWL fields

Revision ID: 041
Revises: 040
Create Date: 2026-08-06

Why
---
PACS audit remediation (docs/PACS_AUDIT-2026-08-06.md):

- ME-04: Referring/Performing physicians were only stored in the files.meta
  JSONB blob (keyed by element name), so QIDO/QR could never filter on them.
  Promote them to first-class study columns, populated at ingest from the
  DICOM tags.
- ME-03: MWL responses omitted ScheduledProcedureStepID / ProtocolName /
  RequestingPhysician — the worklist_entries table had no columns for them.
- HI-07: ORM sync_db drift — the unique UID index set from migration 017 is
  mirrored into the ORM CREATE TABLE paths, and 040's columns already were.

Data Migration
--------------
Existing rows stay NULL until re-ingest; the columns are additive.

Rollback
--------
Drops the five columns.
"""

from alembic import op

revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS referring_physician TEXT")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS performing_physician TEXT")
    op.execute(
        "ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS scheduled_procedure_step_id TEXT DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS protocol_name TEXT DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE worklist_entries ADD COLUMN IF NOT EXISTS requesting_physician TEXT DEFAULT ''"
    )


def downgrade():
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS referring_physician")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS performing_physician")
    op.execute("ALTER TABLE worklist_entries DROP COLUMN IF EXISTS scheduled_procedure_step_id")
    op.execute("ALTER TABLE worklist_entries DROP COLUMN IF EXISTS protocol_name")
    op.execute("ALTER TABLE worklist_entries DROP COLUMN IF EXISTS requesting_physician")
