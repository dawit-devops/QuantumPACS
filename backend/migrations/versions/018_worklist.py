"""Create worklist_entries table for Modality Worklist (MWL)

Revision ID: 018
Revises: 017
Create Date: 2026-07-25

Why
---
Creates the worklist_entries table for DICOM Modality Worklist (MWL) support,
storing scheduled imaging procedures with patient demographics, modality,
scheduled date/time, station AE title, and status tracking.

Data Migration
--------------
None — new table only.

Rollback
--------
Drops the worklist_entries table and its indexes.

References
----------
- DICOM PS3.4: Modality Worklist SOP Class
- ADR-018: Worklist feature design
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS worklist_entries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id TEXT NOT NULL,
        patient_name TEXT NOT NULL DEFAULT '',
        patient_birth_date TEXT DEFAULT '',
        patient_sex TEXT DEFAULT '',
        accession_number TEXT DEFAULT '',
        requested_procedure_id TEXT DEFAULT '',
        requested_procedure_desc TEXT DEFAULT '',
        scheduled_date DATE,
        scheduled_time TIME,
        modality TEXT DEFAULT '',
        station_ae_title TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'scheduled'
            CHECK (status IN ('scheduled', 'performed', 'cancelled')),
        study_uid TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        performed_at TIMESTAMPTZ
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_worklist_accession ON worklist_entries(accession_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worklist_status ON worklist_entries(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worklist_scheduled_date ON worklist_entries(scheduled_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worklist_modality ON worklist_entries(modality)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_worklist_modality")
    op.execute("DROP INDEX IF EXISTS ix_worklist_scheduled_date")
    op.execute("DROP INDEX IF EXISTS ix_worklist_status")
    op.execute("DROP INDEX IF EXISTS ix_worklist_accession")
    op.execute("DROP TABLE IF EXISTS worklist_entries")
