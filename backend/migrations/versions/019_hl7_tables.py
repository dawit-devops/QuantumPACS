"""Create hl7_messages and hl7_parse_errors tables for HL7 audit

Revision ID: 019
Revises: 018
Create Date: 2026-07-26

Why
---
Creates HL7 infrastructure tables: hl7_messages for raw message storage and audit,
hl7_parse_errors for per-field parsing failure tracking — supporting HL7 v2.x
ADT/ORM message ingestion and debugging.

Data Migration
--------------
None — new tables only.

Rollback
--------
Drops both tables and their indexes.

References
----------
- HL7 v2.5: ADT, ORM message specifications
- ADR-019: HL7 integration design
"""

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS hl7_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        raw_hash TEXT NOT NULL,
        raw_content TEXT NOT NULL,
        message_type TEXT DEFAULT '',
        event_type TEXT DEFAULT '',
        patient_id TEXT DEFAULT '',
        accession_number TEXT DEFAULT '',
        sending_facility TEXT DEFAULT '',
        parsed_fields JSONB,
        parse_status TEXT NOT NULL DEFAULT 'ok'
            CHECK (parse_status IN ('ok', 'partial', 'failed')),
        error_message TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_hl7_messages_hash ON hl7_messages(raw_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hl7_messages_type ON hl7_messages(message_type, event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hl7_messages_patient ON hl7_messages(patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hl7_messages_created ON hl7_messages(created_at)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS hl7_parse_errors (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        hl7_message_id UUID REFERENCES hl7_messages(id) ON DELETE CASCADE,
        segment TEXT DEFAULT '',
        field_number INT DEFAULT 0,
        field_name TEXT DEFAULT '',
        raw_value TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_hl7_parse_errors_msg ON hl7_parse_errors(hl7_message_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_hl7_parse_errors_msg")
    op.execute("DROP TABLE IF EXISTS hl7_parse_errors")
    op.execute("DROP INDEX IF EXISTS ix_hl7_messages_hash")
    op.execute("DROP INDEX IF EXISTS ix_hl7_messages_type")
    op.execute("DROP INDEX IF EXISTS ix_hl7_messages_patient")
    op.execute("DROP INDEX IF EXISTS ix_hl7_messages_created")
    op.execute("DROP TABLE IF EXISTS hl7_messages")
