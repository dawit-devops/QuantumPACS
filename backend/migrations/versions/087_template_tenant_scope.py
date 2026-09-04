"""Tenant-scope ris_report_templates (A3, GAP_AUDIT_TDD_PIPELINE.md)

Revision ID: 087
Revises: 086
Create Date: 2026-08-22

publish_version() (R2-02-07/09) UPDATEs ris_report_templates filtered by
tenant_id, but migration 071 never created that column — every publish/
rollback on a migrated DB raised UndefinedColumnError AFTER inserting the
version row, leaving history and the activated body divergent. The column
arrives with DEFAULT 'default', backfilling the seeded templates; parity
with ris_report_template_versions (which already carries tenant_id).
"""

from alembic import op

revision = '087'
down_revision = '086'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE ris_report_templates"
        " ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_templates_tenant_modality"
        " ON ris_report_templates(tenant_id, modality)"
    )


def downgrade():
    op.execute(
        "DROP INDEX IF EXISTS ix_ris_templates_tenant_modality"
    )
    op.execute(
        "ALTER TABLE ris_report_templates DROP COLUMN IF EXISTS tenant_id"
    )
