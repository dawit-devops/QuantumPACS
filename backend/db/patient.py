from db.conn import get_tenant_slug
from db.table import Table
from pypika.pseudocolumns import PseudoColumn


class Patient(Table):
    name = 'patients'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY,
            patient_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            birth_date TEXT,
            sex TEXT,
            meta JSONB,
            tenant_id TEXT
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS patients_patient_id ON patients(patient_id);
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_patients_tenant ON patients(tenant_id);
        """)
        # S8 (P-01): portal contact fields (mirrors migration 089).
        await self.exec(
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone TEXT"
        )
        await self.exec(
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS email TEXT"
        )

    async def insert_or_select(self, data):
        q = self.insert().columns(
            'patient_id', 'name', 'birth_date', 'sex', 'tenant_id',
        ).insert((
            data['patient_id'], data['patient_name'],
            data['patient_birth_date'], data['patient_sex'],
            get_tenant_slug() or 'default',
        ),).on_conflict('patient_id').do_update(
            self.table.name, PseudoColumn('EXCLUDED.name'),
        ).returning('id')

        patient_id = await self.fetchval(q)
        return {'id': patient_id}

    async def get_by_mrn(self, mrn: str):
        """Lightweight lookup by MRN (patient_id) for scheduling engine."""
        q = self.select('*').where(self.table.patient_id == mrn)
        return await self.fetchone(q)

    async def get_extra(self, patient_id):
        q = self.select('*').where(self.table.id == patient_id)
        patient = await self.fetchone(q)
        if not patient:
            return None
        patient = dict(patient)
        pid = patient['id']

        rows = await self.conn.fetch("""
            SELECT
                s.id AS study_id,
                s.study_id AS study_uid,
                s.description AS study_desc,
                s.study_instance_uid,
                s.accession_number,
                se.id AS series_id,
                se.number AS series_number,
                se.modality AS series_modality,
                se.description AS series_desc,
                se.series_instance_uid,
                f.id AS file_id,
                f.name AS file_name,
                f.hash AS file_hash,
                f.indexed,
                f.sop_instance_uid,
                f.deleted,
                f.meta,
                f.tools_state
            FROM studies s
            LEFT JOIN series se ON se.study_id = s.id
            LEFT JOIN files f ON f.series_id = se.id
            WHERE s.patient_id = $1
            ORDER BY s.id, se.id, f.id
        """, pid)

        studies = {}
        series_map = {}
        for row in rows:
            sid = row['study_id']
            if sid not in studies:
                studies[sid] = {
                    'id': sid, 'study_id': row['study_uid'],
                    'description': row['study_desc'],
                    'study_instance_uid': row['study_instance_uid'],
                    'accession_number': row['accession_number'],
                    'series': [],
                }
            seid = row['series_id']
            if seid is not None and seid not in series_map:
                series_map[seid] = {
                    'id': seid, 'study_id': sid,
                    'number': row['series_number'],
                    'modality': row['series_modality'],
                    'description': row['series_desc'],
                    'series_instance_uid': row['series_instance_uid'],
                    'files': [],
                }
            if row['file_id'] is not None:
                series_map[seid]['files'].append({
                    'id': row['file_id'],
                    'name': row['file_name'],
                    'hash': row['file_hash'],
                    'indexed': row['indexed'],
                    'sop_instance_uid': row['sop_instance_uid'],
                    'deleted': row['deleted'],
                    'meta': row['meta'],
                    'tools_state': row['tools_state'],
                })

        for sid, s in studies.items():
            s['series'] = [v for v in series_map.values() if v['study_id'] == sid]

        patient['studies'] = list(studies.values())
        # Care-coordinator review (P2-1): patient-scoped report list for the
        # patient page's Reports & Results card (REPORT_READ-gated in the UI).
        # exams.patient_id carries the MRN (patients.patient_id), unlike
        # studies.patient_id which references the numeric patients.id.
        # Guarded: some callers (exam detail) mock/serialize a patient row
        # without the MRN column — reports enrichment is a patient-page nicety.
        if patient.get('patient_id'):
            patient['reports'] = [
                dict(r) for r in await self.conn.fetch(
                    """
                    SELECT r.id, r.exam_id, r.status, r.created_at, r.signed_at,
                           e.accession_number, e.modality,
                           e.requested_procedure_desc AS procedure_desc
                    FROM reports r
                    JOIN exams e ON e.id = r.exam_id
                    WHERE e.patient_id = $1
                    ORDER BY r.created_at DESC
                    """,
                    patient['patient_id'],
                )
            ]
        return patient
