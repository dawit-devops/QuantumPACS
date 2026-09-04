"""FK ris_appointments.order_id -> ris_orders (S4 C-4)

Revision ID: 076
Revises: 075
Create Date: 2026-08-20

Why
---
C-4: ris_appointments.order_id is a bare UUID with no referential
integrity — a booking can reference a deleted/never-existing order and
the engine's post-insert lifecycle transition then fails after the
appointment exists. The FK makes dangling references impossible at the
DB level (order-less bookings keep NULL).

Before adding the constraint, any pre-existing dangling order_ids are
cleared (their appointment rows are already broken — no order to show,
no lifecycle to transition). The dev database currently has zero
violations; the guard keeps fresh databases from failing the upgrade.

Rollback
--------
Drops the constraint.
"""

from alembic import op

revision = '076'
down_revision = '075'

def upgrade():
    op.execute(
        'ALTER TABLE ris_appointments '
        'DROP CONSTRAINT IF EXISTS ris_appointments_order_id_fkey')
    op.execute(
        'UPDATE ris_appointments SET order_id = NULL '
        'WHERE order_id IS NOT NULL '
        'AND NOT EXISTS (SELECT 1 FROM ris_orders o WHERE o.id = order_id)')
    op.execute(
        'ALTER TABLE ris_appointments '
        'ADD CONSTRAINT ris_appointments_order_id_fkey '
        'FOREIGN KEY (order_id) REFERENCES ris_orders(id)')


def downgrade():
    op.execute(
        'ALTER TABLE ris_appointments '
        'DROP CONSTRAINT IF EXISTS ris_appointments_order_id_fkey')
