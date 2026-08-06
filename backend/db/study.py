from db.table import Table
from pypika.pseudocolumns import PseudoColumn


class Study(Table):
    name = 'studies'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS studies (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            study_id TEXT NOT NULL,
            description TEXT,
            study_instance_uid TEXT,
            accession_number TEXT,
            study_date TEXT,
            UNIQUE(patient_id, study_id)
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS studies_study_id ON studies(study_id);
        """)

    async def insert_or_select(self, data):
        q = self.insert().columns(
            'patient_id', 'study_id', 'description',
            'study_instance_uid', 'accession_number', 'study_date',
        ).insert((
            # patient_id column references the patients row created just before
            # this call — Files.add() sets patient_db_id, not study_db_id.
            data['patient_db_id'], data['study_id'], data.get('study_description', ''),
            data.get('study_instance_uid', ''), data.get('accession_number', ''),
            data.get('study_date', ''),
        ), ).on_conflict(
            'patient_id, study_id'
        ).do_update(
            self.table.description, PseudoColumn('EXCLUDED.description'),
        ).returning('id')

        sid = await self.fetchval(q)
        return {'id': sid}
