"""Add DICOM UID columns to studies, series, files

Revision ID: 017
Revises: 016
Create Date: 2026-07-25

Adds:
- studies.study_instance_uid, studies.accession_number
- series.series_instance_uid
- files.sop_instance_uid
"""

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS study_instance_uid TEXT")
    op.execute("ALTER TABLE studies ADD COLUMN IF NOT EXISTS accession_number TEXT")
    op.execute("ALTER TABLE series ADD COLUMN IF NOT EXISTS series_instance_uid TEXT")
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS sop_instance_uid TEXT")

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_studies_study_instance_uid "
        "ON studies(study_instance_uid) WHERE study_instance_uid IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_series_series_instance_uid "
        "ON series(series_instance_uid) WHERE series_instance_uid IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_files_sop_instance_uid "
        "ON files(sop_instance_uid) WHERE sop_instance_uid IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_studies_accession_number "
        "ON studies(accession_number)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_studies_accession_number")
    op.execute("DROP INDEX IF EXISTS ix_files_sop_instance_uid")
    op.execute("DROP INDEX IF EXISTS ix_series_series_instance_uid")
    op.execute("DROP INDEX IF EXISTS ix_studies_study_instance_uid")

    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS sop_instance_uid")
    op.execute("ALTER TABLE series DROP COLUMN IF EXISTS series_instance_uid")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS accession_number")
    op.execute("ALTER TABLE studies DROP COLUMN IF EXISTS study_instance_uid")
