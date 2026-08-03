"""Create QA tables + extend incidents/protocols for the R05 QA team workflow

Revision ID: 036
Revises: 035
Create Date: 2026-08-03

Why
---
Implements the R05 QI/QA Team workflow (FR-R05-01..07, FR-R05-10): a QA review
queue over completed exams, structured QA scoring that feeds the R03 protocol
compliance scorecard, corrective actions, QA incident logging (with the
resolved lifecycle), and a protocol registry CRUD with protocol codes + ACR
benchmarks.

Tables
------
- qa_scores: one row per reviewed exam (pass/fail, dose, sequence compliance)
- corrective_actions: R03/R05/R06-sourced actions assigned to the QA team
- incidents: extended with study_uids + resolved lifecycle (FR-R05-06)
- protocols: extended with protocol_code + CTDIvol/SNR benchmarks (FR-R05-03)

Rollback
--------
Drops qa_scores + corrective_actions and removes the added columns.

References
----------
- docs/requirements/qa-team/ (R05 package, artifacts 01-08)
"""

from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS qa_scores (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        protocol_id UUID,
        pass_fail TEXT NOT NULL DEFAULT 'pass'
            CHECK (pass_fail IN ('pass', 'fail', 'skipped')),
        discrepancy_level TEXT NOT NULL DEFAULT 'none'
            CHECK (discrepancy_level IN ('none', 'minor', 'major', 'critical')),
        dose_dlp FLOAT DEFAULT 0,
        dose_ctdivol FLOAT DEFAULT 0,
        dose_kvp FLOAT DEFAULT 0,
        dose_mas FLOAT DEFAULT 0,
        sequence_compliance JSONB DEFAULT '{}'::jsonb,
        comments TEXT DEFAULT '',
        reviewed_by TEXT DEFAULT '',
        reviewed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_qa_scores_exam ON qa_scores(exam_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_qa_scores_reviewed ON qa_scores(reviewed_at)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS corrective_actions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        source TEXT NOT NULL DEFAULT 'R05_self'
            CHECK (source IN ('R03', 'R05_self', 'R06')),
        issue TEXT NOT NULL,
        study_uids JSONB DEFAULT '[]'::jsonb,
        assigned_to TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'in_progress', 'resolved')),
        findings TEXT DEFAULT '',
        actions_taken TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        resolved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_corrective_actions_status ON corrective_actions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_corrective_actions_assigned ON corrective_actions(assigned_to)")

    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS study_uid TEXT DEFAULT ''")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS repeat_study_uid TEXT DEFAULT ''")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open' "
               "CHECK (status IN ('open', 'in_progress', 'resolved'))")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolution_notes TEXT DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_status ON incidents(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_type ON incidents(incident_type)")

    op.execute("ALTER TABLE protocols ADD COLUMN IF NOT EXISTS protocol_code TEXT DEFAULT ''")
    op.execute("ALTER TABLE protocols ADD COLUMN IF NOT EXISTS acr_benchmark_ctdivol FLOAT")
    op.execute("ALTER TABLE protocols ADD COLUMN IF NOT EXISTS acr_benchmark_min_snr FLOAT")
    op.execute("ALTER TABLE protocols ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    # Partial unique index: only enforce uniqueness when a code is set
    # (seeded R06 protocols have empty codes).
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_protocols_code "
               "ON protocols(protocol_code) WHERE protocol_code != ''")


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_qa_scores_exam")
    op.execute("DROP INDEX IF EXISTS ix_qa_scores_reviewed")
    op.execute("DROP TABLE IF EXISTS qa_scores")
    op.execute("DROP INDEX IF EXISTS ix_corrective_actions_status")
    op.execute("DROP INDEX IF EXISTS ix_corrective_actions_assigned")
    op.execute("DROP TABLE IF EXISTS corrective_actions")
    op.execute("DROP INDEX IF EXISTS ix_incidents_type")
    op.execute("DROP INDEX IF EXISTS ix_incidents_status")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS resolution_notes")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS resolved_at")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS repeat_study_uid")
    op.execute("ALTER TABLE incidents DROP COLUMN IF EXISTS study_uid")
    op.execute("DROP INDEX IF EXISTS uq_protocols_code")
    op.execute("ALTER TABLE protocols DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE protocols DROP COLUMN IF EXISTS acr_benchmark_min_snr")
    op.execute("ALTER TABLE protocols DROP COLUMN IF EXISTS acr_benchmark_ctdivol")
    op.execute("ALTER TABLE protocols DROP COLUMN IF EXISTS protocol_code")
