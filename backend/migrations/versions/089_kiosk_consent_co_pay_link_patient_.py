"""kiosk consent + co-pay link + patient contact

Revision ID: 089
Revises: 088
Create Date: 2026-08-24 00:27:58.157360

"""
from typing import Sequence, Union

from alembic import op


revision: str = '089'
down_revision: Union[str, None] = '088'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # S2 (K-03): kiosk digital consent — signature image, acceptance flag,
    # and optional decline reason, stored per appointment.
    # ADD COLUMN IF NOT EXISTS — sync_db() may have created these on a
    # drifted dev database.
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS consent_signature TEXT"
    )
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS consent_accepted BOOLEAN"
    )
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS consent_decline_reason TEXT"
    )
    op.execute(
        "ALTER TABLE ris_appointments "
        "ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ"
    )
    # S4 (K-04): kiosk co-pay — the invoice is linked to the RIS order so the
    # token-scoped payment path can find the patient's invoice from the
    # appointment's order without exposing billing internals to the kiosk.
    op.execute(
        "ALTER TABLE invoice "
        "ADD COLUMN IF NOT EXISTS order_id TEXT"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_invoice_order_id ON invoice(order_id)"
    )
    # S8 (P-01): patient contact fields for the portal profile — the front
    # desk captures them at registration, the portal displays read-only.
    op.execute(
        "ALTER TABLE patients "
        "ADD COLUMN IF NOT EXISTS phone TEXT"
    )
    op.execute(
        "ALTER TABLE patients "
        "ADD COLUMN IF NOT EXISTS email TEXT"
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