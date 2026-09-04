"""RIS appointments — conflict-free booking table (S4-09)

Revision ID: 069
Revises: 068
Create Date: 2026-08-19

Why
---
The scheduling engine (S4-10) must never double-book a resource:
RIS-SL-34 requires 0 double-books. The guarantee is enforced by an
EXCLUDE constraint over (tenant_id, resource_id, tstzrange(start,end))
backed by a GiST index, which also serves the availability search.
btree_gist supplies the = operators for the scalar columns. Links to
ris_orders via order_id so appointment -> worklist creation (S4-13)
and order status transitions (S4-03) can join through.

The DDL is raw SQL so the migration and db/ris_appointments.sync_db()
produce identical schema — the dev DB is bootstrapped by sync_db while
containers bootstrap by alembic, and the EXCLUDE constraint syntax is
not expressible through sqlalchemy.op.create_table.

Rollback
--------
Drops the table. Safe: no production data exists yet (feature not shipped).
"""

from alembic import op

revision = '069'
down_revision = '068'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    op.execute("""
    CREATE TABLE IF NOT EXISTS ris_appointments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT,
        order_id UUID,
        resource_id UUID NOT NULL REFERENCES ris_resources(id) ON DELETE CASCADE,
        patient_id TEXT NOT NULL,
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ NOT NULL,
        status TEXT NOT NULL DEFAULT 'SCHEDULED'
            CHECK (status IN ('SCHEDULED', 'ARRIVED', 'IN_PROGRESS',
                              'COMPLETED', 'CANCELLED')),
        reason TEXT DEFAULT '',
        override_reason TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now(),
        CONSTRAINT no_double_book EXCLUDE USING gist (
            tenant_id WITH =,
            resource_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        )
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_appointments_patient
        ON ris_appointments (patient_id, start_time)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_ris_appointments_order
        ON ris_appointments (order_id)
    """)


def downgrade():
    op.drop_table('ris_appointments')