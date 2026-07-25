from datetime import datetime, timezone

from db.table import Table


class Worklist(Table):
    name = 'worklist_entries'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS worklist_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            patient_name TEXT NOT NULL DEFAULT '',
            patient_birth_date TEXT DEFAULT '',
            patient_sex TEXT DEFAULT '',
            accession_number TEXT DEFAULT '',
            requested_procedure_id TEXT DEFAULT '',
            requested_procedure_desc TEXT DEFAULT '',
            scheduled_date DATE,
            scheduled_time TIME,
            modality TEXT DEFAULT '',
            station_ae_title TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled', 'performed', 'cancelled')),
            study_uid TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            performed_at TIMESTAMPTZ
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_worklist_accession ON worklist_entries(accession_number)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_worklist_status ON worklist_entries(status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_worklist_scheduled_date ON worklist_entries(scheduled_date)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_worklist_modality ON worklist_entries(modality)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'patient_id', 'patient_name', 'patient_birth_date', 'patient_sex',
            'accession_number', 'requested_procedure_id', 'requested_procedure_desc',
            'scheduled_date', 'scheduled_time', 'modality', 'station_ae_title',
            'status', 'created_by', 'created_at', 'updated_at',
        ).insert((
            data['patient_id'],
            data.get('patient_name', ''),
            data.get('patient_birth_date', ''),
            data.get('patient_sex', ''),
            data.get('accession_number', ''),
            data.get('requested_procedure_id', ''),
            data.get('requested_procedure_desc', ''),
            data.get('scheduled_date'),
            data.get('scheduled_time'),
            data.get('modality', ''),
            data.get('station_ae_title', ''),
            data.get('status', 'scheduled'),
            data.get('created_by', ''),
            now, now,
        ),).returning('id')
        eid = await self.fetchval(q)
        return {'id': eid}

    async def search(self, status=None, modality=None, date_from=None, date_to=None,
                     search=None, page=1, per_page=20):
        from pypika import Order, Query as PypikaQuery
        q = PypikaQuery.from_(self.table).select(
            self.table.star,
        ).orderby(self.table.scheduled_date, order=Order.desc)

        if status:
            q = q.where(self.table.status == status)
        if modality:
            q = q.where(self.table.modality == modality)
        if date_from:
            q = q.where(self.table.scheduled_date >= date_from)
        if date_to:
            q = q.where(self.table.scheduled_date <= date_to)
        if search:
            like = f'%{search}%'
            q = q.where(
                (self.table.patient_name.ilike(like)) |
                (self.table.patient_id.ilike(like)) |
                (self.table.accession_number.ilike(like))
            )

        q = q.limit(per_page).offset((page - 1) * per_page)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def mark_performed(self, accession_number, study_uid):
        now = datetime.now(timezone.utc)
        q = self.update().where(
            self.table.accession_number == accession_number,
        ).where(
            self.table.status == 'scheduled',
        ).set(
            self.table.status, 'performed',
        ).set(
            self.table.study_uid, study_uid,
        ).set(
            self.table.performed_at, now,
        ).set(
            self.table.updated_at, now,
        )
        await self.exec(q)

    async def get_by_accession(self, accession_number):
        q = self.select(self.table.star).where(
            self.table.accession_number == accession_number,
        )
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def cancel(self, entry_id):
        now = datetime.now(timezone.utc)
        q = self.update().where(
            self.table.id == entry_id,
        ).set(
            self.table.status, 'cancelled',
        ).set(
            self.table.updated_at, now,
        )
        await self.exec(q)
