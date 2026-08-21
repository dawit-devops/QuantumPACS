"""RIS Reminders & Message Log — ris_message_log, ris_reminder_config (R2-02)

Revision ID: 079
Revises: 078
Create Date: 2026-08-21

Why
---
E-RIS2-02 (R2-01-10..13) adds outbound patient/operational reminders
(SMS/email/phone) with a send/receipt audit trail. ris_message_log records
every attempted delivery (channel, recipient, event, status SENT/FAILED,
attempts, provider receipt) so failures are retryable and auditable
(RIS-SL-60). ris_reminder_config stores the per-tenant channel + template
settings the frontend edits (R2-01-10). Opt-out is honored through the
existing notification_prefs table (event_type scoped), reusing the
bell's per-event toggle rather than duplicating it.

Follows the codebase tenant_id convention (no facilities table), matching
ris_prior_auth_requests / ris_charges.

Rollback
--------
Drops ris_message_log and ris_reminder_config.
"""

from alembic import op

revision = '079'
down_revision = '078'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE ris_message_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        channel TEXT NOT NULL DEFAULT 'email'
            CHECK (channel IN ('sms', 'email', 'phone')),
        recipient TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL DEFAULT '',
        subject TEXT DEFAULT '',
        body TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'SENT'
            CHECK (status IN ('SENT', 'FAILED')),
        attempts INTEGER NOT NULL DEFAULT 1,
        provider_receipt TEXT DEFAULT '',
        sent_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_message_log_tenant_status '
        'ON ris_message_log(tenant_id, status, sent_at)')
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_message_log_recipient '
        'ON ris_message_log(recipient)')
    op.execute("""
    CREATE TABLE ris_reminder_config (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT DEFAULT 'default',
        event_type TEXT NOT NULL,
        channel TEXT NOT NULL DEFAULT 'email'
            CHECK (channel IN ('sms', 'email', 'phone')),
        template TEXT DEFAULT '',
        lead_time_hours INTEGER NOT NULL DEFAULT 24,
        active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (tenant_id, event_type)
    )
    """)


def downgrade():
    op.drop_table('ris_reminder_config')
    op.drop_table('ris_message_log')
