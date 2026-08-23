"""kiosk consent + co-pay link + patient contact

Revision ID: 089
Revises: 088
Create Date: 2026-08-24 00:27:58.157360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '089'
down_revision: Union[str, None] = '088'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # S2 (K-03): kiosk digital consent — signature image, acceptance flag,
    # and optional decline reason, stored per appointment.
    op.add_column(
        'ris_appointments',
        sa.Column('consent_signature', sa.Text(), nullable=True,
                  server_default=None),
    )
    op.add_column(
        'ris_appointments',
        sa.Column('consent_accepted', sa.Boolean(), nullable=True,
                  server_default=None),
    )
    op.add_column(
        'ris_appointments',
        sa.Column('consent_decline_reason', sa.Text(), nullable=True,
                  server_default=None),
    )
    op.add_column(
        'ris_appointments',
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True,
                  server_default=None),
    )


def downgrade() -> None:
    op.drop_column('ris_appointments', 'consent_at')
    op.drop_column('ris_appointments', 'consent_decline_reason')
    op.drop_column('ris_appointments', 'consent_accepted')
    op.drop_column('ris_appointments', 'consent_signature')