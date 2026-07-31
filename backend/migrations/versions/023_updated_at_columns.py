"""Add updated_at columns for FHIR _lastUpdated support

Revision ID: 023
Revises: 022
Create Date: 2026-07-26

Why
---
Adds created_at/updated_at columns to patients, studies, and shared_files tables
to support the FHIR _lastUpdated search parameter for incremental data synchronization.

Data Migration
--------------
None — new columns with DEFAULT now().

Rollback
--------
Drops indexes and columns.

References
----------
- HL7 FHIR R4: _lastUpdated search parameter
"""

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE shared_files ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("CREATE INDEX IF NOT EXISTS ix_patients_updated_at ON patients(updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_studies_updated_at ON studies(updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shared_files_updated_at ON shared_files(updated_at)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_patients_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_studies_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_shared_files_updated_at")
    op.execute("ALTER TABLE patients DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE patients DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE shared_files DROP COLUMN IF EXISTS updated_at")
