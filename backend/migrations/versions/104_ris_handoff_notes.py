"""RIS handoff notes table — CC-08 coordinator handoff notes.

Revision ID: 104
Revises: 103
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md CC-08) needs coordinator
handoff notes on patients — visible to the next coordinator, with
priority flags (low/normal/high/urgent) and read/unread tracking.
This table is intentionally named ris_handoff_notes (not handoff_notes,
which is a legacy nursing table with a different shape).

Rollback
--------
DROP TABLE ris_handoff_notes. Safe: no production data (feature not shipped).
"""

from alembic import op

revision = '104'
down_revision = '103'
branch_labels = None
depends_on = None

PRIORITIES = ('low', 'normal', 'high', 'urgent')


def upgrade():
    # CREATE TABLE IF NOT EXISTS — the repo's sync_db() may have created the
    # table already on a drifted dev database; keep this idempotent.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_handoff_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            patient_id TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_handoff_notes_patient "
        "ON ris_handoff_notes(patient_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ris_handoff_notes_tenant "
        "ON ris_handoff_notes(tenant_id, created_at DESC)")


def downgrade():
    op.drop_table('ris_handoff_notes')
