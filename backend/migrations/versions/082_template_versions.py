"""Report-template versioning — publish + rollback (v1.1 R2-02-07/09)

Revision ID: 082
Revises: 081
Create Date: 2026-08-22

Templates are clinical artifacts; edits must be versioned and reversible.
ris_report_template_versions is append-only; the template row always
reflects the ACTIVE version so readers pay no join.

Rollback: drop the versions table (history is intentionally lost on
downgrade — this is a v1.1 convenience layer).
"""

from alembic import op

revision = '082'
down_revision = '081'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_report_template_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        template_id UUID NOT NULL REFERENCES ris_report_templates(id)
            ON DELETE CASCADE,
        version_number INTEGER NOT NULL,
        findings_template TEXT DEFAULT '',
        impression_template TEXT DEFAULT '',
        published_by TEXT DEFAULT '',
        published_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (template_id, version_number)
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_ris_tversions_template '
        'ON ris_report_template_versions(template_id, version_number DESC)')


def downgrade():
    op.execute('DROP TABLE IF EXISTS ris_report_template_versions')
