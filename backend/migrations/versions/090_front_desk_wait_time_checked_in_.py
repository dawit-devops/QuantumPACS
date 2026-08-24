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
import sqlalchemy as sa


revision: str = '090'
down_revision: Union[str, None] = '089'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ris_appointments',
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=None),
    )
    op.add_column(
        'visits',
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=None),
    )


def downgrade() -> None:
    op.drop_column('visits', 'checked_in_at')
    op.drop_column('ris_appointments', 'checked_in_at')
