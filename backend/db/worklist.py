from datetime import datetime, timezone

from db.conn import get_tenant_slug
from db.table import Table
from pypika import Case, Order


def _mwl_like(value):
    """Translate DICOM C-FIND wildcards to SQL LIKE patterns."""
    return value.replace('%', '').replace('_', '').replace('*', '%').replace('?', '_')


# S6-02: STAT entries must sort first in MWL results.
# Priority codes from HL7 OBR-27.7: S/STAT, A/ASAP, U/URGENT, R/Routine.
PRIORITY_SORT_ORDER = {
    'STAT': 0, 'S': 0,
    'A': 1, 'ASAP': 1, 'U': 1, 'URGENT': 1, 'T': 1,
    'B': 2,  # callback
    'R': 3, 'ROUTINE': 3, '': 3,
}


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
            requested_procedure_priority TEXT DEFAULT '',
            reason_for_requested_procedure TEXT DEFAULT '',
            requested_procedure_code TEXT DEFAULT '',
            requested_procedure_code_meaning TEXT DEFAULT '',
            requested_procedure_code_scheme TEXT DEFAULT '',
            scheduled_procedure_step_id TEXT DEFAULT '',
            protocol_name TEXT DEFAULT '',
            requesting_physician TEXT DEFAULT '',
            referring_physician TEXT DEFAULT '',
            scheduled_station_name TEXT DEFAULT '',
            scheduled_performing_physician TEXT DEFAULT '',
            scheduled_date DATE,
            scheduled_time TIME,
            modality TEXT DEFAULT '',
            station_ae_title TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled', 'in_progress', 'performed', 'cancelled')),
            study_uid TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            performed_at TIMESTAMPTZ,
            tenant_id TEXT
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
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_worklist_tenant ON worklist_entries(tenant_id)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'patient_id', 'patient_name', 'patient_birth_date', 'patient_sex',
            'accession_number', 'requested_procedure_id', 'requested_procedure_desc',
            'requested_procedure_priority', 'reason_for_requested_procedure',
            'requested_procedure_code', 'requested_procedure_code_meaning',
            'requested_procedure_code_scheme',
            'scheduled_procedure_step_id', 'protocol_name', 'requesting_physician',
            'referring_physician', 'scheduled_station_name',
            'scheduled_performing_physician',
            'scheduled_date', 'scheduled_time', 'modality', 'station_ae_title',
            'status', 'created_by', 'created_at', 'updated_at', 'tenant_id',
        ).insert((
            data['patient_id'],
            data.get('patient_name', ''),
            data.get('patient_birth_date', ''),
            data.get('patient_sex', ''),
            data.get('accession_number', ''),
            data.get('requested_procedure_id', ''),
            data.get('requested_procedure_desc', ''),
            data.get('requested_procedure_priority', ''),
            data.get('reason_for_requested_procedure', ''),
            data.get('requested_procedure_code', ''),
            data.get('requested_procedure_code_meaning', ''),
            data.get('requested_procedure_code_scheme', ''),
            data.get('scheduled_procedure_step_id', ''),
            data.get('protocol_name', ''),
            data.get('requesting_physician', ''),
            data.get('referring_physician', ''),
            data.get('scheduled_station_name', ''),
            data.get('scheduled_performing_physician', ''),
            data.get('scheduled_date'),
            data.get('scheduled_time'),
            data.get('modality', ''),
            data.get('station_ae_title', ''),
            data.get('status', 'scheduled'),
            data.get('created_by', ''),
            now, now,
            get_tenant_slug() or 'default',
        ),).returning('id')
        eid = await self.fetchval(q)
        return {'id': eid}

    async def update_entry(self, entry_id, data):
        """Update the mutable scheduling fields of an entry.

        Used by ORM re-order/update messages so a duplicate ORM no longer
        silently drops the corrected scheduling data. Named update_entry to
        avoid shadowing the pypika Table.update() builder used by
        mark_performed/cancel.
        """
        allowed = {
            'patient_id', 'patient_name', 'patient_birth_date', 'patient_sex',
            'accession_number', 'requested_procedure_id', 'requested_procedure_desc',
            'requested_procedure_priority', 'reason_for_requested_procedure',
            'requested_procedure_code', 'requested_procedure_code_meaning',
            'requested_procedure_code_scheme',
            'scheduled_procedure_step_id', 'protocol_name', 'requesting_physician',
            'referring_physician', 'scheduled_station_name',
            'scheduled_performing_physician',
            'scheduled_date', 'scheduled_time', 'modality', 'station_ae_title',
        }
        updates = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not updates:
            return
        now = datetime.now(timezone.utc)
        keys = list(updates.keys()) + ['updated_at']
        values = list(updates.values()) + [now]
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(keys))
        await self.conn.execute(
            f"UPDATE worklist_entries SET {set_clause} WHERE id = $1",
            entry_id, *values,
        )

    async def search(self, status=None, modality=None, station_ae_title=None,
                     date_from=None, date_to=None,
                     time_from=None, time_to=None, search=None, patient_id=None,
                     patient_name=None, requested_procedure_id=None,
                     page=1, per_page=20):
        from pypika import Order, Query as PypikaQuery, functions as fn

        conditions = []
        if status:
            conditions.append(self.table.status == status)
        if modality:
            conditions.append(self.table.modality == modality)
        if station_ae_title:
            conditions.append(self.table.station_ae_title == station_ae_title)
        if date_from:
            conditions.append(self.table.scheduled_date >= date_from)
        if date_to:
            conditions.append(self.table.scheduled_date <= date_to)
        if time_from:
            conditions.append(self.table.scheduled_time >= time_from)
        if time_to:
            conditions.append(self.table.scheduled_time <= time_to)
        if patient_id:
            conditions.append(self.table.patient_id.ilike(_mwl_like(patient_id)))
        if patient_name:
            # DICOM MWL matching treats a bare name as a leading wildcard.
            name_pattern = _mwl_like(patient_name.strip())
            if not name_pattern.endswith('%'):
                name_pattern += '%'
            conditions.append(self.table.patient_name.ilike(name_pattern))
        if requested_procedure_id:
            conditions.append(self.table.requested_procedure_id == requested_procedure_id)
        if search:
            like = f'%{_mwl_like(search)}%'
            conditions.append(
                (self.table.patient_name.ilike(like)) |
                (self.table.patient_id.ilike(like)) |
                (self.table.accession_number.ilike(like))
            )

        # S6-02: STAT entries sort first, then by scheduled date/time.
        priority_expr = (
            Case()
            .when(self.table.requested_procedure_priority.isin(['STAT', 'S']), 0)
            .when(self.table.requested_procedure_priority.isin(['A', 'ASAP', 'U', 'URGENT', 'T']), 1)
            .when(self.table.requested_procedure_priority == 'B', 2)
            .else_(3)
        )
        q = PypikaQuery.from_(self.table).select(
            self.table.star,
        ).orderby(priority_expr, order=Order.asc).orderby(
            self.table.scheduled_date, order=Order.desc,
        ).orderby(self.table.scheduled_time, order=Order.desc)
        for c in conditions:
            q = q.where(c)
        q = q.limit(per_page).offset((page - 1) * per_page)
        rows = await self.fetch(q)

        count_q = PypikaQuery.from_(self.table).select(fn.Count(1))
        for c in conditions:
            count_q = count_q.where(c)
        total = await self.fetchval(count_q) or 0

        return [dict(r) for r in rows], total

    async def get_station_aes(self):
        q = self.select('station_ae_title').where(
            self.table.station_ae_title != ''
        ).distinct().orderby(self.table.station_ae_title)
        rows = await self.fetch(q)
        return [r['station_ae_title'] for r in rows]

    async def mark_in_progress(self, accession_number, study_uid):
        now = datetime.now(timezone.utc)
        q = self.update().where(
            self.table.accession_number == accession_number,
        ).where(
            self.table.status == 'scheduled',
        ).set(
            self.table.status, 'in_progress',
        ).set(
            self.table.study_uid, study_uid,
        ).set(
            self.table.updated_at, now,
        )
        await self.exec(q)

    async def mark_performed(self, accession_number, study_uid=''):
        now = datetime.now(timezone.utc)
        sets = [
            (self.table.status, 'performed'),
            (self.table.performed_at, now),
            (self.table.updated_at, now),
        ]
        if study_uid:
            sets.append((self.table.study_uid, study_uid))
        q = self.update().where(
            self.table.accession_number == accession_number,
        ).where(
            (self.table.status == 'scheduled') | (self.table.status == 'in_progress'),
        )
        for column, value in sets:
            q = q.set(column, value)
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
