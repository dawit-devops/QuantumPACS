"""Seed data for the combined technologist + radiologist interactive E2E.

Creates one patient (E2E-RAD-001) carrying two studies/exams:

- E2E-RAD-CT-1 — status 'ready', assigned to test.technologist: target of the
  technologist console flow (acquire -> QA -> safety -> complete).
- E2E-RAD-MR-1 — status 'completed': second reading target so the radiologist
  console can demonstrate Sign & Next advancing the queue.

Both exams match a seeded studies/series/files row backed by a real DICOM
fixture copied into the storage area, so the radiologist's reading console
renders actual pixels through the exam->imaging bridge (the bridge joins
studies.accession_number = exams.accession_number AND patients.patient_id =
exams.patient_id).

Idempotent: re-runs skip anything already seeded (keyed by accession and
SOPInstanceUID). Usage:
    backend/venv/bin/python backend/seed_e2e.py [--allow-docker]
"""
import argparse
import asyncio
import os
import shutil
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])

from config import is_docker
from db.database import Database

BACKEND_DIR = __file__.rsplit('/', 1)[0]
FIXTURE_DCM = os.path.abspath(
    os.path.join(BACKEND_DIR, '../frontend/e2e/fixtures/fixture-ct-001.dcm')
)
STORAGE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '../data/files'))

SOP_CLASS_CT_IMAGE = '1.2.840.10008.5.1.4.1.1.2'

# test.technologist users.id (see seed_test_users.py)
TECHNOLOGIST = '37'

PATIENT = {
    'patient_id': 'E2E-RAD-001',
    'name': 'E2E^Combined^Flow',
    'birth_date': '19850101',
    'sex': 'F',
}

EXAMS = [
    {
        'accession': 'E2E-RAD-CT-1',
        'study_id': 'E2E-RAD-ST-CT-1',
        'study_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-ct-1',
        'series_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-ct-1-s',
        'series_number': '1',
        'dcm_name': 'e2e-rad-ct-001.dcm',
        'sop_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-ct-1-sop',
        'modality': 'CT',
        'description': 'E2E combined CT head',
        'protocol': 'CT Head — Routine',
        'procedure': 'CT Head',
        'status': 'ready',
        'completed_at': None,
    },
    {
        'accession': 'E2E-RAD-MR-1',
        'study_id': 'E2E-RAD-ST-MR-1',
        'study_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-mr-1',
        'series_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-mr-1-s',
        'series_number': '1',
        'dcm_name': 'e2e-rad-mr-001.dcm',
        'sop_instance_uid': '1.2.826.0.1.3680043.8.498.20260814-e2e-rad-mr-1-sop',
        'modality': 'MR',
        'description': 'E2E combined MRI brain',
        'protocol': 'MRI Brain — Routine',
        'procedure': 'MRI Brain',
        'status': 'completed',
        'completed_at': 'now()',
    },
]


async def reset(conn) -> None:
    """Remove every E2E-RAD-* row so a fresh run starts clean.

    Children are deleted before parents; tables that don't exist in a given
    schema are skipped (schema drift across environments).
    """
    exam_ids = (
        "SELECT id FROM exams WHERE patient_id = "
        f"'{PATIENT['patient_id']}'"
    )
    file_ids = (
        "SELECT id FROM files WHERE patient_id IN "
        f"(SELECT id FROM patients WHERE patient_id = '{PATIENT['patient_id']}')"
    )
    study_ids = (
        "SELECT id FROM studies WHERE patient_id IN "
        f"(SELECT id FROM patients WHERE patient_id = '{PATIENT['patient_id']}')"
    )

    deletes = (
        ('reports', f'exam_id IN ({exam_ids})'),
        ('acquisitions', f'exam_id IN ({exam_ids})'),
        ('safety_checks', f'exam_id IN ({exam_ids})'),
        ('safety_confirmations', f'exam_id IN ({exam_ids})'),
        ('incidents', f'exam_id IN ({exam_ids})'),
        ('exam_dose_records', f'exam_id IN ({exam_ids})'),
        ('replica_files', f'file_id IN ({file_ids})'),
        ('files',
         "patient_id IN (SELECT id FROM patients WHERE patient_id = "
         f"'{PATIENT['patient_id']}')"),
        ('series', f'study_id IN ({study_ids})'),
        ('studies',
         "patient_id IN (SELECT id FROM patients WHERE patient_id = "
         f"'{PATIENT['patient_id']}')"),
        ('exams', f'patient_id = \'{PATIENT["patient_id"]}\''),
        ('worklist_entries', f'patient_id = \'{PATIENT["patient_id"]}\''),
        ('patients', f'patient_id = \'{PATIENT["patient_id"]}\''),
    )
    for table, where in deletes:
        exists = await conn.fetchval(
            'SELECT to_regclass($1)', f'public.{table}',
        )
        if exists:
            await conn.execute(f'DELETE FROM {table} WHERE {where}')


async def seed(allow_docker: bool = False, fixture: str = FIXTURE_DCM,
               do_reset: bool = False):
    if is_docker() and not allow_docker:
        print('Refusing to run in a docker/QUANTUMPACS_DOCKER environment. '
              'Pass --allow-docker (or set QUANTUMPACS_SEED_ALLOW=1) to '
              'override for test environments.', file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(fixture):
        print(f'DICOM fixture not found: {fixture}', file=sys.stderr)
        sys.exit(1)

    db = Database()
    await db.setup(pool_size=4)
    try:
        async with db.acquire() as conn:
            if do_reset:
                await reset(conn)
                print('reset: removed existing E2E-RAD-* rows')
            pid = await conn.fetchval(
                """
                INSERT INTO patients (patient_id, name, birth_date, sex)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (patient_id) DO UPDATE SET
                    name = EXCLUDED.name, birth_date = EXCLUDED.birth_date,
                    sex = EXCLUDED.sex
                RETURNING id
                """,
                PATIENT['patient_id'], PATIENT['name'],
                PATIENT['birth_date'], PATIENT['sex'],
            )
            print(f'patient {PATIENT["patient_id"]} (db id {pid})')

            for spec in EXAMS:
                accession = spec['accession']

                study_id = await conn.fetchval(
                    """
                    INSERT INTO studies (patient_id, study_id, description,
                        study_instance_uid, accession_number, study_date,
                        received_instances, expected_instances, study_status)
                    VALUES ($1, $2, $3, $4, $5, '20260814', 1, 1, 'complete')
                    ON CONFLICT (patient_id, study_id) DO UPDATE SET
                        study_status = EXCLUDED.study_status
                    RETURNING id
                    """,
                    pid, spec['study_id'], spec['description'],
                    spec['study_instance_uid'], accession,
                )
                series_id = await conn.fetchval(
                    """
                    INSERT INTO series (study_id, number, modality, description,
                        series_instance_uid)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (study_id, number) DO UPDATE SET
                        modality = EXCLUDED.modality
                    RETURNING id
                    """,
                    study_id, spec['series_number'], spec['modality'],
                    spec['description'], spec['series_instance_uid'],
                )

                sop = spec['sop_instance_uid']
                file_id = await conn.fetchval(
                    'SELECT id FROM files WHERE sop_instance_uid = $1', sop,
                )
                dcm_path = os.path.join(
                    STORAGE_DIR, PATIENT['patient_id'],
                    spec['study_id'], spec['series_number'], spec['dcm_name'],
                )
                if file_id is None:
                    os.makedirs(os.path.dirname(dcm_path), exist_ok=True)
                    if not os.path.isfile(dcm_path):
                        shutil.copyfile(fixture, dcm_path)
                    size = os.path.getsize(dcm_path)
                    file_id = await conn.fetchval(
                        """
                        INSERT INTO files (patient_id, study_id, series_id,
                            name, hash, sop_instance_uid, sop_class_uid, size,
                            indexed, meta)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, false, '{}'::jsonb)
                        RETURNING id
                        """,
                        pid, study_id, series_id, spec['dcm_name'],
                        f'e2e-rad-hash-{accession}', sop, SOP_CLASS_CT_IMAGE, size,
                    )
                    print(f'  {accession}: file id {file_id} -> {dcm_path}')
                else:
                    print(f'  {accession}: file already present (id {file_id})')

                # ServeFile resolves through replica_files on the master
                # replica; SQL-seeded rows need the mapping to be servable.
                master = await conn.fetchrow(
                    'SELECT id FROM replicas WHERE master = true',
                )
                if master:
                    await conn.execute(
                        """
                        INSERT INTO replica_files (replica_id, file_id,
                            location, status, meta)
                        VALUES ($1, $2, $3, 1, '{}'::jsonb)
                        ON CONFLICT (replica_id, file_id) DO UPDATE SET
                            location = EXCLUDED.location, status = EXCLUDED.status,
                            meta = EXCLUDED.meta
                        """,
                        master['id'], file_id, dcm_path,
                    )
                    print(f'  {accession}: registered on master replica {master["id"]}')

                existing_entry = await conn.fetchval(
                    'SELECT id FROM worklist_entries WHERE accession_number = $1',
                    accession,
                )
                if existing_entry:
                    entry_id = existing_entry
                else:
                    entry_id = await conn.fetchval(
                        """
                        INSERT INTO worklist_entries (patient_id, patient_name,
                            patient_birth_date, patient_sex, accession_number,
                            requested_procedure_id, requested_procedure_desc,
                            scheduled_date, scheduled_time, modality, station_ae_title,
                            status, study_uid, created_by, protocol_name,
                            requesting_physician, requested_procedure_priority)
                        VALUES ($1, $2, $3, $4, $5, '', $6, '20260814', '0900',
                            $7, '', $8, $9, $10, $11, 'Lee^Kim', 'routine')
                        RETURNING id
                        """,
                        PATIENT['patient_id'], PATIENT['name'],
                        PATIENT['birth_date'], PATIENT['sex'], accession,
                        spec['procedure'], spec['modality'],
                        'performed' if spec['status'] == 'completed' else 'scheduled',
                        spec['study_instance_uid'], TECHNOLOGIST, spec['protocol'],
                    )
                completed_at = (
                    'now()' if spec['status'] == 'completed' else 'NULL'
                )
                existing_exam = await conn.fetchval(
                    'SELECT id FROM exams WHERE accession_number = $1', accession,
                )
                if existing_exam:
                    print(f'  {accession}: exam already present (id {existing_exam}), skipping')
                else:
                    exam_id = await conn.fetchval(
                        f"""
                        INSERT INTO exams (worklist_entry_id, patient_id,
                            patient_name, patient_birth_date, patient_sex,
                            accession_number, requested_procedure_desc, modality,
                            station_ae_title, priority, protocol_name, status,
                            assigned_technologist, created_by, referring_physician,
                            completed_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, '', 'routine', $9,
                            $10, $11, $11, 'Lee^Kim', {completed_at})
                        RETURNING id
                        """,
                        entry_id, PATIENT['patient_id'], PATIENT['name'],
                        PATIENT['birth_date'], PATIENT['sex'], accession,
                        spec['procedure'], spec['modality'], spec['protocol'],
                        spec['status'], TECHNOLOGIST,
                    )
                    print(f'  {accession}: exam {exam_id} ({spec["status"]})')
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-docker', action='store_true',
                        help='override the docker guard for test environments')
    parser.add_argument('--fixture', default=FIXTURE_DCM,
                        help='path to the DICOM fixture to copy into storage')
    parser.add_argument('--reset', action='store_true',
                        help='delete existing E2E-RAD-* rows before seeding')
    args = parser.parse_args()
    asyncio.run(seed(allow_docker=args.allow_docker, fixture=args.fixture,
                     do_reset=args.reset))


if __name__ == '__main__':
    main()