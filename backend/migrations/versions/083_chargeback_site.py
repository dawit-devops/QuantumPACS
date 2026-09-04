"""Chargeback site capture on bookings (v1.1 R2-03-08)

Revision ID: 083
Revises: 082
Create Date: 2026-08-22

Bookings write to the servicing site's data plane; requesting_tenant
preserves who ordered the exam so cross-facility activity can be
billed back. Empty on legacy rows (home == servicing).
"""

from alembic import op

revision = '083'
down_revision = '082'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE ris_appointments ADD COLUMN IF NOT EXISTS '
        "requesting_tenant TEXT DEFAULT ''")


def downgrade():
    op.execute('ALTER TABLE ris_appointments '
               'DROP COLUMN IF EXISTS requesting_tenant')
