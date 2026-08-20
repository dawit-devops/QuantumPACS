"""RIS Reporting & Templates — extensions for Sprint S8–S9 (S8-01, S8-06, S8-08)

Revision ID: 071
Revises: 070
Create Date: 2026-08-20

Why
---
Sprint S8–S9 implements structured radiologist reporting, report versioning,
template library management, electronic sign-off, and distribution stubs.
This migration adds necessary columns to `reports` and creates tables for
`ris_report_templates` and `ris_report_versions`.

Rollback
--------
Drops created tables and added columns.
"""

from alembic import op

revision = '071'
down_revision = '070'
branch_labels = None
depends_on = None


def upgrade():
    # S8-01: Extend reports table
    op.execute("""
    ALTER TABLE reports
        ADD COLUMN IF NOT EXISTS ris_order_id UUID,
        ADD COLUMN IF NOT EXISTS template_id UUID,
        ADD COLUMN IF NOT EXISTS distributed_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_reports_ris_order ON reports(ris_order_id)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_reports_is_critical ON reports(is_critical)
        WHERE is_critical = TRUE
    """)

    # S8-06: Create ris_report_templates table
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_report_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        modality TEXT NOT NULL,
        body_part TEXT DEFAULT '',
        findings_template TEXT DEFAULT '',
        impression_template TEXT DEFAULT '',
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_templates_modality
        ON ris_report_templates(modality)
    """)

    # S8-08: Create ris_report_versions table
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_report_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID NOT NULL,
        version_number INT NOT NULL DEFAULT 1,
        findings TEXT DEFAULT '',
        impression TEXT DEFAULT '',
        recommendations TEXT DEFAULT '',
        edited_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_report_versions_report
        ON ris_report_versions(report_id)
    """)


def downgrade():
    op.drop_table('ris_report_versions')
    op.drop_table('ris_report_templates')
    op.execute("""
    ALTER TABLE reports
        DROP COLUMN IF EXISTS ris_order_id,
        DROP COLUMN IF EXISTS template_id,
        DROP COLUMN IF EXISTS distributed_at,
        DROP COLUMN IF EXISTS is_critical
    """)
