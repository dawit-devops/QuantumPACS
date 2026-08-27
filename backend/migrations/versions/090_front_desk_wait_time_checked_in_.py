"""front desk wait-time: checked_in_at on ris_appointments

Revision ID: 090
Revises: 089
Create Date: 2026-08-24 00:30:00.000000

FD-05: the SCHEDULED -> ARRIVED transition stamps checked_in_at so the
tracking board and front-desk queue can compute minutes-since-arrival and
color-code by wait time (green <15m, amber 15-30m, red >30m).
"""
from typing import Sequence, Union

from alembic import op


revision: str = '090'
down_revision: Union[str, None] = '089'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD COLUMN IF NOT EXISTS — sync_db() may have created the appointment
    # column on a drifted dev database.
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE visits "
        "ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ"
    )
    # FD-02: insurance coverage fields — provider/member_id/copay/deductible
    # so eligibility returns real coverage data instead of a hardcoded stub.
    op.execute(
        "ALTER TABLE insurance_records "
        "ADD COLUMN IF NOT EXISTS provider TEXT"
    )
    op.execute(
        "ALTER TABLE insurance_records "
        "ADD COLUMN IF NOT EXISTS member_id TEXT"
    )
    op.execute(
        "ALTER TABLE insurance_records "
        "ADD COLUMN IF NOT EXISTS copay_amount NUMERIC(10, 2)"
    )
    op.execute(
        "ALTER TABLE insurance_records "
        "ADD COLUMN IF NOT EXISTS deductible_total NUMERIC(10, 2)"
    )
    op.execute(
        "ALTER TABLE insurance_records "
        "ADD COLUMN IF NOT EXISTS deductible_remaining NUMERIC(10, 2)"
    )


def downgrade() -> None:
    op.drop_column('insurance_records', 'deductible_remaining')
    op.drop_column('insurance_records', 'deductible_total')
    op.drop_column('insurance_records', 'copay_amount')
    op.drop_column('insurance_records', 'member_id')
    op.drop_column('insurance_records', 'provider')
    op.drop_column('visits', 'checked_in_at')
    op.drop_column('ris_appointments', 'checked_in_at')
