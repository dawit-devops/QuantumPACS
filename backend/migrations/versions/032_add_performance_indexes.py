"""Add performance indexes for common query patterns

Revision ID: 032
Revises: 031
Create Date: 2026-07-30

Why:
- Add CONCURRENTLY indexes (non-blocking in production) for common query patterns:
  files.sop_instance_uid, series.series_instance_uid, studies.study_instance_uid,
  worklist_entries.status, and logs JSON event_type (GIN index).

Data migration: None (index-only change, built CONCURRENTLY to avoid table locks).

Rollback: DROP each index (plain DROP, no CONCURRENTLY needed).

References:
- Performance optimization (v3 sprint 6)
"""

from alembic import op

revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY cannot run inside a transaction block; alembic wraps
    # migrations in one by default, so run these outside it.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_files_sop_instance_uid "
            "ON files(sop_instance_uid) WHERE sop_instance_uid IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_series_instance_uid "
            "ON series(series_instance_uid) WHERE series_instance_uid IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_studies_study_instance_uid "
            "ON studies(study_instance_uid) WHERE study_instance_uid IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_worklist_entries_status "
            "ON worklist_entries(status)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_audit_log_event_type "
            "ON logs USING gin ((log::jsonb) jsonb_path_ops)"
        )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_files_sop_instance_uid")
    op.execute("DROP INDEX IF EXISTS ix_series_instance_uid")
    op.execute("DROP INDEX IF EXISTS ix_studies_study_instance_uid")
    op.execute("DROP INDEX IF EXISTS ix_worklist_entries_status")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_event_type")
