from db.conn import get_tenant_slug
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
            referring_physician TEXT,
            performing_physician TEXT,
            received_instances INTEGER NOT NULL DEFAULT 0,
            expected_instances INTEGER NOT NULL DEFAULT 0,
            study_status TEXT NOT NULL DEFAULT 'receiving'
                CHECK (study_status IN ('receiving', 'complete', 'incomplete')),
            tenant_id TEXT,
            UNIQUE(patient_id, study_id)
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS studies_study_id ON studies(study_id);
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_studies_study_status ON studies(study_status)
        """)
        # Parity with migrations 017/040.
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_studies_study_instance_uid
        ON studies(study_instance_uid) WHERE study_instance_uid IS NOT NULL
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_studies_accession_number
        ON studies(accession_number)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_studies_tenant ON studies(tenant_id);
        """)

    async def insert_or_select(self, data):
        q = self.insert().columns(
            'patient_id', 'study_id', 'description',
            'study_instance_uid', 'accession_number', 'study_date',
            'referring_physician', 'performing_physician', 'tenant_id',
        ).insert((
            # patient_id column references the patients row created just before
            # this call — Files.add() sets patient_db_id, not study_db_id.
            data['patient_db_id'], data['study_id'], data.get('study_description', ''),
            data.get('study_instance_uid', ''), data.get('accession_number', ''),
            data.get('study_date', ''),
            data.get('referring_physician', ''), data.get('performing_physician', ''),
            get_tenant_slug() or 'default',
        ),         ).on_conflict(
            'patient_id', 'study_id'
        ).do_update(
            self.table.description, PseudoColumn('EXCLUDED.description'),
        ).returning('id')

        sid = await self.fetchval(q)
        return {'id': sid}
