"""HIM release policy on reports (v1.1 R2-05-05 → v2.0 enforcement)

Revision ID: 084
Revises: 083
Create Date: 2026-08-22

release_status drives patient-bound visibility:
  auto     — default; signed reports flow out as before
  held     — HIM review hold; excluded from FHIR bundles and share flows
  released — explicitly cleared by HIM after a hold

Rollback drops the column (hold state is operational, not archival).
"""

from alembic import op

revision = '084'
down_revision = '083'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE reports ADD COLUMN IF NOT EXISTS release_status
        TEXT NOT NULL DEFAULT 'auto'
        CHECK (release_status IN ('auto', 'held', 'released'))
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_reports_held '
        'ON reports(release_status) WHERE release_status = \'held\'')


def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_reports_held')
    op.execute('ALTER TABLE reports DROP COLUMN IF EXISTS release_status')
