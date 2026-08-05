"""Create exam lifecycle tables for the R06 technologist workflow

Revision ID: 033
Revises: 032
Create Date: 2026-08-03

Why
---
Implements the R06 Radiology Technologist exam lifecycle (FR-R06-01..10): a
patient exam progresses through identity verification, protocol selection,
image acquisition + QA, dose documentation, safety checks, and completion with
handoff to the radiologist. Supports retake/incident logging and emergency
protocol overrides.

Tables
------
- exams: one row per imaging exam, linked to a worklist entry when adopted
- acquisitions: per-series image acquisition records with dose parameters
- safety_checks: pre-contrast allergy/pregnancy confirmations
- incidents: retake/incident logging (R05 QA notification on high/critical)
- protocol_overrides: audited emergency protocol overrides
- protocols: modality protocol registry

Data Migration
--------------
None — new tables only. Protocol registry is seeded by the API at startup
when empty (idempotent).

Rollback
--------
Drops all six tables and their indexes.

References
----------
- docs/requirements/technologist/ (R06 package, artifacts 01-08)
"""

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        worklist_entry_id UUID,
        patient_id TEXT NOT NULL,
        patient_name TEXT NOT NULL DEFAULT '',
        patient_birth_date TEXT DEFAULT '',
        patient_sex TEXT DEFAULT '',
        accession_number TEXT DEFAULT '',
        requested_procedure_desc TEXT DEFAULT '',
        modality TEXT DEFAULT '',
        station_ae_title TEXT DEFAULT '',
        priority TEXT NOT NULL DEFAULT 'routine'
            CHECK (priority IN ('routine', 'urgent', 'stat')),
        protocol_name TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'ready'
            CHECK (status IN ('ready', 'in_progress', 'completed', 'cancelled')),
        assigned_technologist TEXT DEFAULT '',
        identity_confirmed_at TIMESTAMPTZ,
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_status ON exams(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_technologist ON exams(assigned_technologist)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_accession ON exams(accession_number)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS acquisitions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        series_number INT NOT NULL DEFAULT 1,
        instance_uid TEXT DEFAULT '',
        description TEXT DEFAULT '',
        kvp FLOAT DEFAULT 0,
        mas FLOAT DEFAULT 0,
        dlp FLOAT DEFAULT 0,
        ctdivol FLOAT DEFAULT 0,
        exposure_time FLOAT DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'accepted', 'rejected')),
        reject_reason TEXT DEFAULT '',
        acquired_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_acquisitions_exam ON acquisitions(exam_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS safety_checks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        check_item TEXT NOT NULL,
        answer TEXT NOT NULL,
        notes TEXT DEFAULT '',
        checked_by TEXT DEFAULT '',
        checked_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_safety_checks_exam ON safety_checks(exam_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        incident_type TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'medium'
            CHECK (severity IN ('low', 'medium', 'high', 'critical')),
        description TEXT NOT NULL,
        reported_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_exam ON incidents(exam_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS protocol_overrides (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID NOT NULL,
        justification TEXT NOT NULL,
        original_params JSONB DEFAULT '{}'::jsonb,
        overridden_params JSONB DEFAULT '{}'::jsonb,
        overridden_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocol_overrides_exam ON protocol_overrides(exam_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS protocols (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        modality TEXT NOT NULL,
        body_part TEXT DEFAULT '',
        sequences JSONB DEFAULT '[]'::jsonb,
        parameters JSONB DEFAULT '{}'::jsonb,
        acr_benchmark_dlp FLOAT,
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocols_modality ON protocols(modality)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_protocols_modality")
    op.execute("DROP TABLE IF EXISTS protocols")
    op.execute("DROP INDEX IF EXISTS ix_protocol_overrides_exam")
    op.execute("DROP TABLE IF EXISTS protocol_overrides")
    op.execute("DROP INDEX IF EXISTS ix_incidents_exam")
    op.execute("DROP TABLE IF EXISTS incidents")
    op.execute("DROP INDEX IF EXISTS ix_safety_checks_exam")
    op.execute("DROP TABLE IF EXISTS safety_checks")
    op.execute("DROP INDEX IF EXISTS ix_acquisitions_exam")
    op.execute("DROP TABLE IF EXISTS acquisitions")
    op.execute("DROP INDEX IF EXISTS ix_exams_status")
    op.execute("DROP INDEX IF EXISTS ix_exams_technologist")
    op.execute("DROP INDEX IF EXISTS ix_exams_accession")
    op.execute("DROP TABLE IF EXISTS exams")
