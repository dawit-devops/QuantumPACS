"""Database access for the R08 Front Desk workflows — patient registration,
visits, order intake, appointment scheduling with capacity conflict detection,
consent capture, insurance/guarantor records and the waiting queue.

Plain query helpers over the migration 037 tables (visits, visit_orders,
appointments, consent_documents, insurance_records, modality_capacity).
No Table base class: these tables are owned by Alembic, not sync_db().
"""
from datetime import datetime, timezone


class FrontDesk:
    def __init__(self, conn):
        self.conn = conn

    # ---- patients ----

    async def search_patients(self, q, limit=50):
        like = f'%{q}%'
        rows = await self.conn.fetch(
            """
            SELECT id, patient_id, name, birth_date, sex
            FROM patients
            WHERE name ILIKE $1 OR patient_id ILIKE $1
            ORDER BY name
            LIMIT $2
            """,
            like, limit,
        )
        return rows

    async def create_patient(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO patients (patient_id, name, birth_date, sex, meta)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, patient_id, name, birth_date, sex
            """,
            data['patient_id'], data['name'], data.get('birth_date', ''),
            data.get('sex', ''), data.get('meta'),
        )

    async def find_patient_duplicate(self, name, birth_date):
        """Exact demographic match for the MPI pre-check (R5-13) — a patient
        with the same name and date of birth is presumed to be the same
        person regardless of the MRN seen. Only meaningful when a birth date
        was actually captured; empty dates never match."""
        if not birth_date:
            return None
        return await self.conn.fetchrow(
            """
            SELECT id, patient_id, name, birth_date, sex
            FROM patients
            WHERE name = $1 AND birth_date = $2
            ORDER BY created_at
            LIMIT 1
            """,
            name, birth_date,
        )

    async def get_patient(self, patient_id):
        return await self.conn.fetchrow(
            "SELECT id, patient_id, name, birth_date, sex FROM patients WHERE patient_id = $1",
            patient_id,
        )

    # ---- visits ----

    async def list_visits(self, status=None, date=None, page=1, per_page=20):
        where = []
        params = []
        if status:
            params.append(status)
            where.append(f"status = ${len(params)}")
        if date:
            params.append(date)
            where.append(f"visit_date = ${len(params)}::date")
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        rows = await self.conn.fetch(
            f"""
            SELECT * FROM visits {where_sql}
            ORDER BY created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """,
            *params, per_page, (page - 1) * per_page,
        )
        total = await self.conn.fetchval(
            f"SELECT COUNT(1) FROM visits {where_sql}",
            *params,
        ) or 0
        return rows, total

    async def create_visit(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO visits (patient_id, visit_date, destination_room, status,
                                hl7_sync_status, created_by)
            VALUES ($1, COALESCE($2, CURRENT_DATE), COALESCE($3, ''), COALESCE($4, 'registered'),
                    COALESCE($5, 'pending'), $6)
            RETURNING *
            """,
            data['patient_id'], data.get('visit_date'), data.get('destination_room'),
            data.get('status'), data.get('hl7_sync_status'), data.get('created_by', ''),
        )

    async def get_visit(self, visit_id):
        return await self.conn.fetchrow("SELECT * FROM visits WHERE id = $1", visit_id)

    async def update_visit(self, visit_id, updates):
        now = datetime.now(timezone.utc)
        keys = list(updates.keys()) + ['updated_at']
        values = list(updates.values()) + [now]
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        await self.conn.execute(
            f"UPDATE visits SET {set_clause} WHERE id = $1",
            visit_id, *values,
        )

    # ---- consent seeding ----

    async def seed_default_consents(self, visit_id):
        """Seed the three baseline consent documents for a new visit —
        only when the visit has no consent rows yet."""
        existing = await self.conn.fetchval(
            "SELECT COUNT(1) FROM consent_documents WHERE visit_id = $1",
            visit_id,
        )
        if existing:
            return
        for consent_type in ('general_consent', 'privacy_notice', 'procedure_consent'):
            await self.conn.execute(
                "INSERT INTO consent_documents (visit_id, consent_type, status) VALUES ($1, $2, 'required')",
                visit_id, consent_type,
            )

    # ---- visit orders ----

    async def create_order(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO visit_orders (visit_id, patient_id, requested_procedure, indication,
                                      urgency, referring_physician, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            data['visit_id'], data['patient_id'], data['requested_procedure'],
            data.get('indication', ''), data.get('urgency', 'routine'),
            data.get('referring_physician', ''), data.get('created_by', ''),
        )

    async def list_orders(self, visit_id):
        return await self.conn.fetch(
            "SELECT * FROM visit_orders WHERE visit_id = $1 ORDER BY created_at DESC",
            visit_id,
        )

    # ---- appointments / capacity ----

    async def get_capacity(self, modality, day_of_week):
        return await self.conn.fetchval(
            "SELECT MAX(capacity) FROM modality_capacity WHERE modality = $1 AND day_of_week = $2",
            modality, day_of_week,
        )

    async def count_slot_booked(self, modality, scheduled_date, scheduled_time):
        """Booked capacity for a slot. Appointments are the single source of
        truth (R5-01): the mirrored worklist entry is a projection of the
        appointment, so counting it too would double-count every booking."""
        return await self.conn.fetchval(
            """
            SELECT COUNT(1) FROM appointments
            WHERE modality = $1 AND scheduled_date = $2 AND scheduled_time = $3
              AND status != 'cancelled'
            """,
            modality, scheduled_date, scheduled_time,
        )

    async def list_appointments(self, date=None, modality=None, patient_id=None):
        where = []
        params = []
        if date:
            params.append(date)
            where.append(f"scheduled_date = ${len(params)}::date")
        if modality:
            params.append(modality)
            where.append(f"modality = ${len(params)}")
        if patient_id:
            params.append(patient_id)
            where.append(f"patient_id = ${len(params)}")
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        return await self.conn.fetch(
            f"""
            SELECT * FROM appointments {where_sql}
            ORDER BY scheduled_date, scheduled_time
            """,
            *params,
        )

    async def create_appointment(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO appointments (patient_id, visit_id, worklist_entry_id, modality,
                                      room, technologist, scheduled_date, scheduled_time,
                                      status, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'scheduled', $9)
            RETURNING *
            """,
            data['patient_id'], data.get('visit_id'), data.get('worklist_entry_id'),
            data['modality'], data.get('room', ''), data.get('technologist', ''),
            data['scheduled_date'], data['scheduled_time'], data.get('created_by', ''),
        )

    async def create_worklist_entry(self, data):
        """Insert a scheduled worklist entry so the appointment feeds the
        R06/R07 modality worklist (accession number generated server-side)."""
        return await self.conn.fetchval(
            """
            INSERT INTO worklist_entries (patient_id, patient_name, patient_birth_date,
                                          patient_sex, scheduled_date, scheduled_time,
                                          modality, station_ae_title, requested_procedure_desc,
                                          accession_number, status, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, '',
                    'ACC-' || upper(substr(md5(random()::text), 1, 10)), 'scheduled', $9)
            RETURNING id
            """,
            data['patient_id'], data.get('patient_name', ''),
            data.get('patient_birth_date', ''), data.get('patient_sex', ''),
            data['scheduled_date'], data['scheduled_time'], data['modality'],
            data.get('station_ae_title', ''), data.get('created_by', ''),
        )

    async def cancel_appointment(self, appointment_id):
        await self.conn.execute(
            "UPDATE appointments SET status = 'cancelled', updated_at = now() WHERE id = $1",
            appointment_id,
        )
        # Keep the mirrored worklist entry in sync so the modality worklist
        # stops presenting a patient whose appointment was cancelled (R5-02).
        await self.conn.execute(
            """
            UPDATE worklist_entries SET status = 'cancelled', updated_at = now()
            WHERE id = (SELECT worklist_entry_id FROM appointments WHERE id = $1)
              AND status = 'scheduled'
            """,
            appointment_id,
        )

    # ---- consents ----

    async def list_consents(self, visit_id):
        return await self.conn.fetch(
            "SELECT * FROM consent_documents WHERE visit_id = $1 ORDER BY created_at DESC",
            visit_id,
        )

    async def create_consent(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO consent_documents (visit_id, consent_type, status, file_name, attached_by)
            VALUES ($1, $2, COALESCE($3, 'attached'), COALESCE($4, ''), $5)
            RETURNING *
            """,
            data['visit_id'], data['consent_type'], data.get('status'),
            data.get('file_name'), data.get('attached_by', ''),
        )

    async def attach_consent(self, visit_id, consent_type, file_name, attached_by):
        """Mark an existing pending consent attached; falls back to inserting
        a new attached record when no matching consent row exists."""
        row = await self.conn.fetchrow(
            """
            SELECT id FROM consent_documents
            WHERE visit_id = $1 AND status = 'required'
              AND ($2 = '' OR consent_type = $2)
            ORDER BY created_at
            LIMIT 1
            """,
            visit_id, consent_type,
        )
        if row:
            await self.conn.execute(
                """
                UPDATE consent_documents
                SET status = 'attached', file_name = $2, attached_by = $3, attached_at = now()
                WHERE id = $1
                """,
                row['id'], file_name, attached_by,
            )
            return await self.conn.fetchrow(
                "SELECT * FROM consent_documents WHERE id = $1",
                row['id'],
            )
        return await self.conn.fetchrow(
            """
            INSERT INTO consent_documents (visit_id, consent_type, status, file_name,
                                           attached_by, attached_at)
            VALUES ($1, COALESCE(NULLIF($2, ''), 'general_consent'), 'attached', $3, $4, now())
            RETURNING *
            """,
            visit_id, consent_type, file_name, attached_by,
        )

    # ---- insurance ----

    async def list_insurance(self, patient_id):
        return await self.conn.fetch(
            "SELECT * FROM insurance_records WHERE patient_id = $1 ORDER BY created_at DESC",
            patient_id,
        )

    async def create_insurance(self, data):
        return await self.conn.fetchrow(
            """
            INSERT INTO insurance_records (patient_id, policy_number, guarantor_name,
                                           authorization_status, authorization_number, notes,
                                           created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            data['patient_id'], data.get('policy_number', ''),
            data.get('guarantor_name', ''), data.get('authorization_status', 'none'),
            data.get('authorization_number', ''), data.get('notes', ''),
            data.get('created_by', ''),
        )

    async def update_insurance(self, insurance_id, updates):
        now = datetime.now(timezone.utc)
        keys = list(updates.keys()) + ['updated_at']
        values = list(updates.values()) + [now]
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        await self.conn.execute(
            f"UPDATE insurance_records SET {set_clause} WHERE id = $1",
            insurance_id, *values,
        )

    # ---- waiting queue ----

    async def waiting_queue(self, date=''):
        """Open visits (registered/checked_in) for the day. The exams join
        added no columns yet multiplied rows (one patient can have many
        exams), so the destination room is fetched per-visit instead (R5-09).
        Completed/archived visits are hidden — the queue shows patients
        waiting to be seen."""
        return await self.conn.fetch(
            """
            SELECT
                v.id AS visit_id,
                v.patient_id,
                p.name AS patient_name,
                v.status,
                COALESCE(
                    (SELECT a.room FROM appointments a
                      WHERE a.visit_id = v.id AND a.status != 'cancelled'
                      ORDER BY a.created_at LIMIT 1),
                    v.destination_room
                ) AS destination,
                v.updated_at,
                v.created_at
            FROM visits v
            LEFT JOIN patients p ON p.patient_id = v.patient_id
            WHERE v.status IN ('registered', 'checked_in')
              AND ($1 = '' OR v.visit_date = $1::date)
            ORDER BY v.created_at
            """,
            date,
        )
