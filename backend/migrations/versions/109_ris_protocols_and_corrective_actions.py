"""RIS protocol registry and corrective actions tables.

Revision ID: 109
Revises: 108
Create Date: 2026-08-27

Why
---
QA-09 (protocol registry with versioning) and QA-11 (corrective actions
with due-date escalation) are the last P0 QA features in the gap audit.
Two tables, one migration: protocols for imaging-protocol CRUD, corrective
actions for tracking QA follow-ups with assignee/due-date/status.

Rollback
--------
DROP TABLE ris_corrective_actions, ris_protocols. Safe: no production
data (features not shipped).
"""

from alembic import op

revision = '109'
down_revision = '108'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_protocols (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            modality TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1,
            is_default BOOLEAN NOT NULL DEFAULT false,
            content TEXT NOT NULL DEFAULT '',
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ris_protocols_modality
            ON ris_protocols (modality)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_corrective_actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            assignee_id TEXT NOT NULL DEFAULT '',
            incident_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled')),
            priority TEXT NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'critical')),
            due_date TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ris_corrective_actions_status
            ON ris_corrective_actions (status, due_date)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ris_corrective_actions_assignee
            ON ris_corrective_actions (assignee_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ris_corrective_actions")
    op.execute("DROP TABLE IF EXISTS ris_protocols")
