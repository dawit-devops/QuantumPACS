"""RIS appointment persistence (S4-09) — ris_appointments.

The booking engine's conflict-free guarantee (RIS-SL-34, 0 double-books)
rests on a Postgres EXCLUDE constraint: two appointments for the same
resource in the same tenant may not have overlapping time ranges. The
GiST index backing the constraint doubles as the availability-search
index. btree_gist provides the = equality operators on tenant_id and
resource_id inside EXCLUDE.
"""
from datetime import datetime, timezone

from db.conn import get_tenant_slug
from db.table import Table


class RisAppointments(Table):
    name = 'ris_appointments'

    async def sync_db(self):
        await self.exec('CREATE EXTENSION IF NOT EXISTS btree_gist')
        await self.exec("""
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
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_appointments_patient
            ON ris_appointments (patient_id, start_time)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_appointments_order
            ON ris_appointments (order_id)
        """)

    async def _ensure_requesting_tenant(self):
        await self.conn.execute(
            "ALTER TABLE ris_appointments ADD COLUMN IF NOT EXISTS "
            "requesting_tenant TEXT DEFAULT ''")

    async def create(self, data):
        now = datetime.now(timezone.utc)
        data = dict(data)
        data.setdefault('tenant_id', get_tenant_slug() or 'default')
        data.setdefault('created_at', now)
        q = self.insert().columns(*data.keys()).insert(*data.values()).returning('*')
        return await self.fetchone(q)

    async def get(self, appointment_id):
        q = self.query().select('*').where(self.table.id == appointment_id)
        return await self.fetchone(q)

    async def list_for_order(self, order_id):
        """All appointments for an order, chronological (S4-02 detail view)."""
        q = (self.query().select('*')
             .where(self.table.order_id == order_id)
             .orderby(self.table.start_time))
        return await self.fetch(q)

    async def for_resource(self, resource_id, day_start, day_end):
        q = self.query().select('*').where(
            (self.table.resource_id == resource_id)
            & (self.table.start_time < day_end)
            & (self.table.end_time > day_start)
        )
        q = q.orderby(self.table.start_time)
        return await self.fetch(q)

    async def update_slot(self, appointment_id, start_time, end_time,
                          reason=''):
        q = (self.update()
             .set(self.table.start_time, start_time)
             .set(self.table.end_time, end_time)
             .set(self.table.reason, reason)
             .where(self.table.id == appointment_id)
             .returning('*'))
        return await self.fetchone(q)

    async def update_status(self, appointment_id, status):
        q = (self.update()
             .set(self.table.status, status)
             .where(self.table.id == appointment_id)
             .returning('*'))
        return await self.fetchone(q)

    async def delete(self, appointment_id):
        return await self.conn.execute(
            'DELETE FROM ris_appointments WHERE id = $1', appointment_id)
    async def stamp_requesting_tenant(self, appointment_id, home_tenant):
        """R2-03-08: record the requester's home site for chargeback."""
        await self.conn.execute(
            "UPDATE ris_appointments SET requesting_tenant = $2 "
            "WHERE id = $1 AND requesting_tenant = ''",
            appointment_id, home_tenant,
        )
