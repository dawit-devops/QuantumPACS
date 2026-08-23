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
    # S4 (K-04): kiosk co-pay — the invoice is linked to the RIS order so the
    # token-scoped payment path can find the patient's invoice from the
    # appointment's order without exposing billing internals to the kiosk.
    op.add_column(
        'invoice',
        sa.Column('order_id', sa.Text(), nullable=True, server_default=None),
    )
    op.create_index(
        'ix_invoice_order_id', 'invoice', ['order_id'],
    )
    # S8 (P-01): patient contact fields for the portal profile — the front
    # desk captures them at registration, the portal displays read-only.
    op.add_column(
        'patients',
        sa.Column('phone', sa.Text(), nullable=True, server_default=None),
    )
    op.add_column(
        'patients',
        sa.Column('email', sa.Text(), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column('patients', 'email')
    op.drop_column('patients', 'phone')
    op.drop_index('ix_invoice_order_id', table_name='invoice')
    op.drop_column('invoice', 'order_id')
    op.drop_column('ris_appointments', 'consent_at')
    op.drop_column('ris_appointments', 'consent_decline_reason')
    op.drop_column('ris_appointments', 'consent_accepted')
    op.drop_column('ris_appointments', 'consent_signature')