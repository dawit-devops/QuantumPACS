"""R10 Biomedical Engineer data access — raw asyncpg SQL against the
equipment registry tables created in migration 037 (equipment,
maintenance_schedules, qc_records, downtime_events, work_orders,
vendor_contracts, parts_inventory)."""
from datetime import datetime, timezone


class Equipment:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self, status=None, modality=None, search=None):
        conditions = []
        params = []
        idx = 1
        if status:
            conditions.append(f"operational_status = ${idx}")
            params.append(status)
            idx += 1
        if modality:
            conditions.append(f"modality = ${idx}")
            params.append(modality)
            idx += 1
        if search:
            like = f'%{search}%'
            conditions.append(
                f"(identifier ILIKE ${idx} OR manufacturer ILIKE ${idx + 1} OR model ILIKE ${idx + 2})"
            )
            params += [like, like, like]
            idx += 3
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        rows = await self.conn.fetch(
            f"SELECT * FROM equipment {where} ORDER BY identifier",
            *params,
        )
        return [dict(r) for r in rows]

    async def get(self, equipment_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM equipment WHERE id = $1",
            equipment_id,
        )
        return dict(row) if row else None

    async def by_identifier(self, identifier):
        row = await self.conn.fetchrow(
            "SELECT id FROM equipment WHERE identifier = $1",
            identifier,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO equipment (identifier, modality, manufacturer, model,
                   serial_number, location, acquisition_date, operational_status,
                   warranty_end_date, created_by, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now(), now())
               RETURNING *""",
            data['identifier'],
            data.get('modality', ''),
            data.get('manufacturer', ''),
            data.get('model', ''),
            data.get('serial_number', ''),
            data.get('location', ''),
            data.get('acquisition_date'),
            data.get('operational_status', 'operational'),
            data.get('warranty_end_date'),
            data.get('created_by', ''),
        )
        return dict(row) if row else None

    async def update(self, equipment_id, updates):
        updates = dict(updates)
        updates['updated_at'] = datetime.now(timezone.utc)
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        await self.conn.execute(
            f"UPDATE equipment SET {set_clause} WHERE id = $1",
            equipment_id, *values,
        )

    async def set_status(self, equipment_id, status):
        await self.conn.execute(
            "UPDATE equipment SET operational_status = $2, updated_at = now() WHERE id = $1",
            equipment_id, status,
        )

    async def set_status_where(self, equipment_id, new_status, current_status):
        await self.conn.execute(
            """UPDATE equipment SET operational_status = $2, updated_at = now()
               WHERE id = $1 AND operational_status = $3""",
            equipment_id, new_status, current_status,
        )


class MaintenanceSchedules:
    def __init__(self, conn=None):
        self.conn = conn

    async def list_pm(self, equipment_id=None):
        where = "AND ms.equipment_id = $1" if equipment_id else ""
        params = (equipment_id,) if equipment_id else ()
        rows = await self.conn.fetch(
            f"""SELECT ms.*, e.identifier, e.modality
                FROM maintenance_schedules ms
                JOIN equipment e ON e.id = ms.equipment_id
                WHERE ms.schedule_type = 'pm' AND ms.status = 'active' {where}
                ORDER BY ms.next_due_date NULLS LAST""",
            *params,
        )
        return [dict(r) for r in rows]

    async def get(self, schedule_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM maintenance_schedules WHERE id = $1",
            schedule_id,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO maintenance_schedules (equipment_id, schedule_type, title,
                   frequency_days, next_due_date, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, 'active', now(), now())
               RETURNING *""",
            data['equipment_id'],
            data.get('schedule_type', 'pm'),
            data.get('title', ''),
            data.get('frequency_days', 90),
            data.get('next_due_date'),
        )
        return dict(row) if row else None

    async def complete(self, schedule_id, completed_by):
        row = await self.conn.fetchrow(
            """UPDATE maintenance_schedules
               SET last_completed_at = now(),
                   completed_by = $2,
                   next_due_date = (now() + make_interval(days => frequency_days))::date,
                   updated_at = now()
               WHERE id = $1
               RETURNING *""",
            schedule_id, completed_by,
        )
        return dict(row) if row else None


class QCRecords:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self, equipment_id, limit=50):
        rows = await self.conn.fetch(
            """SELECT * FROM qc_records
               WHERE equipment_id = $1
               ORDER BY tested_at DESC
               LIMIT $2""",
            equipment_id, limit,
        )
        return [dict(r) for r in rows]

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO qc_records (equipment_id, schedule_id, test_type,
                   pass_fail, measured_values, tested_by, tested_at)
               VALUES ($1, $2, $3, $4, $5, $6, now())
               RETURNING *""",
            data['equipment_id'],
            data.get('schedule_id'),
            data['test_type'],
            data['pass_fail'],
            data.get('measured_values') or {},
            data.get('tested_by', ''),
        )
        return dict(row) if row else None


class DowntimeEvents:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self, equipment_id):
        rows = await self.conn.fetch(
            """SELECT * FROM downtime_events
               WHERE equipment_id = $1
               ORDER BY start_at DESC""",
            equipment_id,
        )
        return [dict(r) for r in rows]

    async def get_open(self, equipment_id):
        row = await self.conn.fetchrow(
            """SELECT * FROM downtime_events
               WHERE equipment_id = $1 AND status = 'open'
               ORDER BY start_at DESC
               LIMIT 1""",
            equipment_id,
        )
        return dict(row) if row else None

    async def get_for_equipment(self, downtime_id, equipment_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM downtime_events WHERE id = $1 AND equipment_id = $2",
            downtime_id, equipment_id,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO downtime_events (equipment_id, start_at, cause_category,
                   impact, status, created_by)
               VALUES ($1, $2, $3, $4, 'open', $5)
               RETURNING *""",
            data['equipment_id'],
            data.get('start_at'),
            data.get('cause_category', ''),
            data.get('impact', ''),
            data.get('created_by', ''),
        )
        return dict(row) if row else None

    async def update(self, downtime_id, updates):
        updates = dict(updates)
        updates['updated_at'] = datetime.now(timezone.utc)
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        row = await self.conn.fetchrow(
            f"UPDATE downtime_events SET {set_clause} WHERE id = $1 RETURNING *",
            downtime_id, *values,
        )
        return dict(row) if row else None

    async def list_open(self):
        rows = await self.conn.fetch(
            """SELECT d.*, e.identifier, e.modality,
                      (now() - d.start_at) > interval '24 hours' AS overdue_24h
               FROM downtime_events d
               JOIN equipment e ON e.id = d.equipment_id
               WHERE d.status = 'open'
               ORDER BY d.start_at""",
        )
        return [dict(r) for r in rows]


class WorkOrders:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self, status=None, equipment_id=None):
        conditions = []
        params = []
        idx = 1
        if status:
            conditions.append(f"wo.status = ${idx}")
            params.append(status)
            idx += 1
        if equipment_id:
            conditions.append(f"wo.equipment_id = ${idx}")
            params.append(equipment_id)
            idx += 1
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        rows = await self.conn.fetch(
            f"""SELECT wo.*, e.identifier
                FROM work_orders wo
                JOIN equipment e ON e.id = wo.equipment_id
                {where}
                ORDER BY wo.created_at DESC""",
            *params,
        )
        return [dict(r) for r in rows]

    async def get(self, work_order_id):
        row = await self.conn.fetchrow(
            """SELECT wo.*, e.identifier
               FROM work_orders wo
               JOIN equipment e ON e.id = wo.equipment_id
               WHERE wo.id = $1""",
            work_order_id,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO work_orders (equipment_id, description, status,
                   assigned_to, notes, created_by, created_at, updated_at)
               VALUES ($1, $2, 'open', '', '', $3, now(), now())
               RETURNING *""",
            data['equipment_id'],
            data['description'],
            data.get('created_by', ''),
        )
        return dict(row) if row else None

    async def update(self, work_order_id, updates):
        updates = dict(updates)
        updates['updated_at'] = datetime.now(timezone.utc)
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        row = await self.conn.fetchrow(
            f"UPDATE work_orders SET {set_clause} WHERE id = $1 RETURNING *",
            work_order_id, *values,
        )
        return dict(row) if row else None


class VendorContracts:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self, equipment_id):
        rows = await self.conn.fetch(
            """SELECT * FROM vendor_contracts
               WHERE equipment_id = $1
               ORDER BY created_at""",
            equipment_id,
        )
        return [dict(r) for r in rows]

    async def get(self, contract_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM vendor_contracts WHERE id = $1",
            contract_id,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO vendor_contracts (equipment_id, vendor_name, coverage_terms,
                   warranty_end_date, response_sla_p1_minutes, response_sla_p2_minutes)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING *""",
            data['equipment_id'],
            data.get('vendor_name', ''),
            data.get('coverage_terms', ''),
            data.get('warranty_end_date'),
            data.get('response_sla_p1_minutes', 15),
            data.get('response_sla_p2_minutes', 240),
        )
        return dict(row) if row else None

    async def update(self, contract_id, updates):
        updates = dict(updates)
        updates['updated_at'] = datetime.now(timezone.utc)
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        row = await self.conn.fetchrow(
            f"UPDATE vendor_contracts SET {set_clause} WHERE id = $1 RETURNING *",
            contract_id, *values,
        )
        return dict(row) if row else None


class PartsInventory:
    def __init__(self, conn=None):
        self.conn = conn

    async def list(self):
        rows = await self.conn.fetch(
            "SELECT * FROM parts_inventory ORDER BY part_name",
        )
        return [dict(r) for r in rows]

    async def get(self, part_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM parts_inventory WHERE id = $1",
            part_id,
        )
        return dict(row) if row else None

    async def create(self, data):
        row = await self.conn.fetchrow(
            """INSERT INTO parts_inventory (part_name, stock_level, low_stock_threshold, unit)
               VALUES ($1, $2, $3, $4)
               RETURNING *""",
            data['part_name'],
            data.get('stock_level', 0),
            data.get('low_stock_threshold', 5),
            data.get('unit', 'unit'),
        )
        return dict(row) if row else None

    async def update(self, part_id, updates):
        updates = dict(updates)
        updates['updated_at'] = datetime.now(timezone.utc)
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        row = await self.conn.fetchrow(
            f"UPDATE parts_inventory SET {set_clause} WHERE id = $1 RETURNING *",
            part_id, *values,
        )
        return dict(row) if row else None


class EquipmentReports:
    def __init__(self, conn=None):
        self.conn = conn

    async def uptime(self, from_date, to_date):
        rows = await self.conn.fetch(
            """SELECT e.identifier, e.modality,
                      COALESCE(SUM(EXTRACT(EPOCH FROM (LEAST(COALESCE(d.end_at, now()), $2::timestamptz)
                                                       - GREATEST(d.start_at, $1::timestamptz)))), 0) AS down_seconds
               FROM equipment e
               LEFT JOIN downtime_events d
                 ON d.equipment_id = e.id
                AND d.start_at < $2::timestamptz
                AND COALESCE(d.end_at, now()) > $1::timestamptz
               GROUP BY e.id, e.identifier, e.modality
               ORDER BY e.identifier""",
            from_date, to_date,
        )
        return [dict(r) for r in rows]

    async def compliance(self, from_date, to_date):
        rows = await self.conn.fetch(
            """SELECT e.identifier, e.modality,
                      (SELECT COUNT(1) FROM maintenance_schedules ms
                        WHERE ms.equipment_id = e.id
                          AND ms.last_completed_at::date >= $1::date
                          AND ms.last_completed_at::date <= $2::date) AS pm_completed,
                      (SELECT COUNT(1) FROM maintenance_schedules ms
                        WHERE ms.equipment_id = e.id
                          AND ((ms.next_due_date >= $1::date AND ms.next_due_date <= $2::date)
                               OR (ms.last_completed_at::date >= $1::date AND ms.last_completed_at::date <= $2::date))) AS pm_scheduled,
                      (SELECT COUNT(1) FROM qc_records qc WHERE qc.equipment_id = e.id) AS qc_total,
                      (SELECT COUNT(1) FROM qc_records qc
                        WHERE qc.equipment_id = e.id AND qc.pass_fail = 'fail') AS qc_failures
               FROM equipment e
               ORDER BY e.identifier""",
            from_date, to_date,
        )
        return [dict(r) for r in rows]

    async def downtime_causes(self, from_date, to_date):
        rows = await self.conn.fetch(
            """SELECT d.cause_category,
                      COUNT(1) AS event_count,
                      COALESCE(SUM(EXTRACT(EPOCH FROM (COALESCE(d.end_at, now()) - d.start_at))), 0) / 60.0 AS total_minutes
               FROM downtime_events d
               WHERE d.start_at < $2::timestamptz
                 AND COALESCE(d.end_at, now()) > $1::timestamptz
               GROUP BY d.cause_category
               ORDER BY event_count DESC""",
            from_date, to_date,
        )
        return [dict(r) for r in rows]
