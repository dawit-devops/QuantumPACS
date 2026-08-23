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
        # S1: kiosk prep instructions (mirrors migration 088). Added via
        # ALTER here so dev db_init paths converge with alembic.
        await self.conn.execute(
            "ALTER TABLE ris_appointments ADD COLUMN IF NOT EXISTS "
            "prep_instructions TEXT DEFAULT ''")

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
        # C4: LEFT JOIN the order's priority onto each block so the day
        # view can render STAT/URGENT badges without a second round-trip.
        rows = await self.conn.fetch(
            """
            SELECT a.*, o.priority AS priority
            FROM ris_appointments a
            LEFT JOIN ris_orders o ON o.id = a.order_id
            WHERE a.resource_id = $1
              AND a.start_time < $3
              AND a.end_time > $2
            ORDER BY a.start_time
            """,
            resource_id, day_start, day_end,
        )
        return [dict(r) for r in rows]

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
    async def chargeback_summary(self, month_start, month_end,
                                 tenant_id='default'):
        """R2-06-04: bookings performed here for OTHER sites, grouped by
        the requesting site — the servicing-side chargeback view."""
        return await self.conn.fetch(
            "SELECT requesting_tenant, count(*) AS bookings "
            "FROM ris_appointments "
            "WHERE tenant_id = $1 AND requesting_tenant <> '' "
            "AND start_time >= $2 AND start_time < $3 "
            "GROUP BY requesting_tenant ORDER BY bookings DESC",
            tenant_id, month_start, month_end,
        )

    async def get_for_checkin(self, appointment_id, tenant_id='default'):
        """RIS-REG-04: kiosk summary — display name, modality, room, prep.
        Minimal PHI: never MRN or order internals. Modality + room live on
        the booked resource (ris_resources), not the appointment row."""
        return await self.conn.fetchrow(
            "SELECT a.id::text AS id, a.status AS status, "
            "a.start_time AS start_time, "
            "COALESCE(r.modality, '') AS modality, "
            "COALESCE(r.location, '') AS room, "
            "COALESCE(a.prep_instructions, '') AS prep_instructions, "
            "COALESCE(p.name, '') AS patient_name "
            "FROM ris_appointments a "
            "LEFT JOIN ris_resources r ON r.id = a.resource_id "
            "LEFT JOIN patients p ON p.patient_id = a.patient_id "
            "AND p.tenant_id = a.tenant_id "
            "WHERE a.id::text = $1 AND a.tenant_id = $2",
            appointment_id, tenant_id)

    async def mark_checked_in(self, appointment_id, tenant_id='default'):
        """Kiosk confirm: SCHEDULED -> ARRIVED; None when not schedulable."""
        return await self.conn.fetchrow(
            "UPDATE ris_appointments SET status = 'ARRIVED' "
            "WHERE id::text = $1 AND tenant_id = $2 AND status = 'SCHEDULED' "
            "RETURNING id::text AS id, status",
            appointment_id, tenant_id)

    async def stamp_requesting_tenant(self, appointment_id, home_tenant):
        """R2-03-08: record the requester's home site for chargeback."""
        await self.conn.execute(
            "UPDATE ris_appointments SET requesting_tenant = $2 "
            "WHERE id = $1 AND requesting_tenant = ''",
            appointment_id, home_tenant,
        )
