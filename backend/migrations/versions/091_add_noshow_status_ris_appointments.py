"""add NO_SHOW status to ris_appointments

Revision ID: 091
Revises: 090
Create Date: 2026-08-24 12:00:00.000000

S-13: no-show tracking — the scheduler marks patients who failed to appear.
NO_SHOW is a terminal status (no further transitions) and frees the slot
for rebooking. The CHECK constraint must be recreated to include the new
literal (Postgres does not support ALTER CHECK).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '091'
down_revision: Union[str, None] = '090'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old CHECK, add the new one with NO_SHOW included.
    op.execute(
        "ALTER TABLE ris_appointments "
        "DROP CONSTRAINT IF EXISTS ris_appointments_status_check"
    )
    op.execute(
        "ALTER TABLE ris_appointments ADD CONSTRAINT "
        "ris_appointments_status_check "
        "CHECK (status IN ('SCHEDULED', 'ARRIVED', 'IN_PROGRESS', "
        "'COMPLETED', 'CANCELLED', 'NO_SHOW'))"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE ris_appointments SET status = 'CANCELLED' "
        "WHERE status = 'NO_SHOW'"
    )
    op.execute(
        "ALTER TABLE ris_appointments "
        "DROP CONSTRAINT IF EXISTS ris_appointments_status_check"
    )
    op.execute(
        "ALTER TABLE ris_appointments ADD CONSTRAINT "
        "ris_appointments_status_check "
        "CHECK (status IN ('SCHEDULED', 'ARRIVED', 'IN_PROGRESS', "
        "'COMPLETED', 'CANCELLED'))"
    )
