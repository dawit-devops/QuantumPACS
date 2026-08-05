"""schema hardening: PKs, indexes, constraints

Revision ID: 002
Revises: 001
Create Date: 2026-07-23

See docs/DB_SCHEMA_REVIEW.md for full rationale.

P0: replica_files.id PRIMARY KEY
P0: UNIQUE on users.username
P0: Missing FK indexes (8)
P1: CHECK constraints on users.status, patients.sex
P2: Composite index for ReplicaFiles sync queries
P3: Drop redundant index on patients.patient_id
"""

from alembic import op


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # R1: Add PK to replica_files (was missing — only had SERIAL, no constraint)
    op.execute("ALTER TABLE replica_files ADD PRIMARY KEY (id)")

    # R2: UNIQUE on users.username (duplicate usernames were possible)
    op.execute("ALTER TABLE users ADD CONSTRAINT users_username_unique UNIQUE (username)")

    # R3: Missing FK indexes (8 indexes)
    op.execute("CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_series_study_id ON series(study_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_files_patient_id ON files(patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_files_study_id ON files(study_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_files_series_id ON files(series_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_file_changes_by_user_id ON file_changes(by_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_replica_files_file_id ON replica_files(file_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_shared_files_file_id ON shared_files(file_id)")

    # R10: Composite index for ReplicaFiles sync queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_rf_replica_status ON replica_files(replica_id, status)")

    # R11: CHECK constraints for domain integrity
    op.execute("ALTER TABLE users ADD CONSTRAINT users_status_check CHECK (status IN ('active', 'deactivated'))")
    op.execute("ALTER TABLE patients ADD CONSTRAINT patients_sex_check CHECK (sex IS NULL OR sex IN ('M', 'F', 'O'))")

    # R15: Drop redundant index — UNIQUE constraint on same column already provides it
    op.execute("DROP INDEX IF EXISTS patients_patient_id")


def downgrade():
    op.execute("ALTER TABLE replica_files DROP CONSTRAINT IF EXISTS replica_files_pkey")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_unique")
    op.execute("DROP INDEX IF EXISTS idx_studies_patient_id")
    op.execute("DROP INDEX IF EXISTS idx_series_study_id")
    op.execute("DROP INDEX IF EXISTS idx_files_patient_id")
    op.execute("DROP INDEX IF EXISTS idx_files_study_id")
    op.execute("DROP INDEX IF EXISTS idx_files_series_id")
    op.execute("DROP INDEX IF EXISTS idx_file_changes_by_user_id")
    op.execute("DROP INDEX IF EXISTS idx_replica_files_file_id")
    op.execute("DROP INDEX IF EXISTS idx_shared_files_file_id")
    op.execute("DROP INDEX IF EXISTS idx_rf_replica_status")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_status_check")
    op.execute("ALTER TABLE patients DROP CONSTRAINT IF EXISTS patients_sex_check")
    op.execute("CREATE INDEX IF NOT EXISTS patients_patient_id ON patients(patient_id)")
