"""Add reminder_sent_at to ris_appointments for portal reminder emitter.

Revision ID: 108
Revises: 107
Create Date: 2026-08-27

Why
---
The portal appointment_reminder emitter trigger needs a per-row timestamp
to prevent double-notifying when the scheduled check runs multiple times.
reminder_sent_at is set to now() after the first successful notification
and NULLed on cancellation (if needed). Idempotent — safe to run on
databases that already have the column (dev db_init paths).
"""

from alembic import op

revision = '108'
down_revision = '107'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ris_appointments "
        "DROP COLUMN IF EXISTS reminder_sent_at"
    )
