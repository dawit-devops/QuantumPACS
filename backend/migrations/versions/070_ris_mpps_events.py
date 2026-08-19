"""RIS MPPS events — audit trail for Modality Performed Procedure Step (S6-08)

Revision ID: 070
Revises: 069
Create Date: 2026-08-20

Why
---
The MPPS consumer (S6-07) receives N-CREATE/N-SET messages from modalities
and must persist every event for audit, troubleshooting, and compliance.
The table captures accession number, event type, MPPS status, study UID,
and the raw DICOM dataset as JSONB.

Rollback
--------
Drops the table. Safe: no production data exists yet.
"""

from alembic import op

revision = '070'
down_revision = '069'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_mpps_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        accession_number TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL DEFAULT '',
        mpps_status TEXT NOT NULL DEFAULT '',
        study_uid TEXT DEFAULT '',
        station_ae_title TEXT DEFAULT '',
        raw_message JSONB DEFAULT '{}',
        tenant_id TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_mpps_accession
        ON ris_mpps_events (accession_number)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_mpps_created
        ON ris_mpps_events (created_at)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_mpps_tenant
        ON ris_mpps_events (tenant_id)
    """)


def downgrade():
    op.drop_table('ris_mpps_events')
