"""Create report + peer review tables for the R12 staff radiologist workflow

Revision ID: 034
Revises: 033
Create Date: 2026-08-03

Why
---
Implements the R12 Staff Radiologist reading workflow (FR-R12-01, FR-R12-09):
exams completed by the technologist land on a priority-sorted reading worklist,
the radiologist drafts/preliminary-signs/final-signs a structured report, and
peers can be assigned a discrepancy-level review of a signed report.

Tables
------
- reports: one report per exam; status machine draft -> preliminary -> final
- report_templates: modality templates for findings/impression sections
- peer_reviews: peer-review assignment with discrepancy level + comment

Data Migration
--------------
None — report templates are seeded by the API at startup when empty.

Rollback
--------
Drops all three tables and their indexes.

References
----------
- docs/requirements/staff-radiologist/ (R12 package, artifacts 01-08)
"""

from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'preliminary', 'final')),
        findings TEXT DEFAULT '',
        impression TEXT DEFAULT '',
        recommendations TEXT DEFAULT '',
        template_name TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        signed_by TEXT DEFAULT '',
        signed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_exam ON reports(exam_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_status ON reports(status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS report_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        modality TEXT NOT NULL,
        body_part TEXT DEFAULT '',
        findings_template TEXT DEFAULT '',
        impression_template TEXT DEFAULT '',
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_report_templates_modality ON report_templates(modality)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS peer_reviews (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        report_id UUID NOT NULL,
        reviewer_id TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'assigned'
            CHECK (status IN ('assigned', 'in_progress', 'completed')),
        discrepancy_level TEXT DEFAULT ''
            CHECK (discrepancy_level IN ('', 'none', 'minor', 'major', 'discrepancy')),
        comment TEXT DEFAULT '',
        assigned_at TIMESTAMPTZ DEFAULT now(),
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_peer_reviews_reviewer ON peer_reviews(reviewer_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_peer_reviews_report ON peer_reviews(report_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_peer_reviews_report")
    op.execute("DROP INDEX IF EXISTS ix_peer_reviews_reviewer")
    op.execute("DROP TABLE IF EXISTS peer_reviews")
    op.execute("DROP INDEX IF EXISTS ix_report_templates_modality")
    op.execute("DROP TABLE IF EXISTS report_templates")
    op.execute("DROP INDEX IF EXISTS ix_reports_status")
    op.execute("DROP INDEX IF EXISTS uq_reports_exam")
    op.execute("DROP TABLE IF EXISTS reports")
