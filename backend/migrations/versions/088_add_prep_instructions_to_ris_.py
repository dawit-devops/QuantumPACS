"""add prep_instructions to ris_appointments + follow-up contact fields

Revision ID: 088
Revises: 087
Create Date: 2026-08-23 23:08:19.586336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '088'
down_revision: Union[str, None] = '087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # S1: kiosk shows modality-specific prep instructions on the check-in
    # screen (ui-ux-redesign-spec 2.13 K-02). Stored per appointment so the
    # scheduling/booking path can author them; the kiosk only reads.
    op.add_column(
        'ris_appointments',
        sa.Column('prep_instructions', sa.Text(), nullable=False,
                  server_default=''),
    )
    # S8: P-05 follow-up contact fields — the coordinator needs the patient's
    # preferred contact method, a free-text note, and a time window.
    op.add_column(
        'follow_up_requests',
        sa.Column('contact_method', sa.Text(), nullable=True,
                  server_default=None),
    )
    op.add_column(
        'follow_up_requests',
        sa.Column('note', sa.Text(), nullable=True, server_default=None),
    )
    op.add_column(
        'follow_up_requests',
        sa.Column('preferred_time', sa.Text(), nullable=True,
                  server_default=None),
    )


def downgrade() -> None:
    op.drop_column('follow_up_requests', 'preferred_time')
    op.drop_column('follow_up_requests', 'note')
    op.drop_column('follow_up_requests', 'contact_method')
    op.drop_column('ris_appointments', 'prep_instructions')
