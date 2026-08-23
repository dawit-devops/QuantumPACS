"""Deterministic demo data for persona UAT walkthroughs (pipeline F4).

One idempotent seed per persona so a UAT owner can reset a single role's
scenario without disturbing the others:

  radiologist    — completed studies w/ real-pixel files, draft + final reports
  technologist   — scheduled/ready/in-progress exams on the worklist
  scheduler      — resources, schedules, appointments, orders (SCHEDULED)
  front-desk     — ARRIVED patients + sign->charge demo data
  biller         — PENDING/BILLED/PAID/DENIED charges + claims + prior-auth
  ris-admin      — templates, coding map, resources
  manager        — cross-status dashboard aggregate (mix of the above)

Personas compose: `--persona all` runs every scenario exactly once. Every
insert is guarded by ON CONFLICT / EXISTS so re-runs are no-ops.

Usage:
    backend/venv/bin/python scripts/seed_uat.py [--allow-docker] [--persona all|radiologist|...]

The docker guard mirrors seed_test_users.py: the shared demo password and
deterministic UAT-* data never touch a deployed runtime unless explicitly
opted in (CI e2e sets QUANTUMPACS_DOCKER + --allow-docker).
"""
import argparse
import asyncio
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import is_docker
from db.database import Database

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
FIXTURE_DCM = os.path.abspath(
    os.path.join(BACKEND_DIR, '../frontend/e2e/fixtures/fixture-ct-001.dcm')
)
STORAGE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '../data/files'))

SOP_CLASS_CT_IMAGE = '1.2.840.10008.5.1.4.1.1.2'

# test.technologist / test.radiologist users.id (see seed_test_users.py).
TECHNOLOGIST_ID = '37'
RADIOLOGIST_ID = '39'

PREFIX = 'UAT-'


def _accession(persona: str, seq: int) -> str:
    return f'{PREFIX}{persona.upper()}-{seq:02d}'


def _patient_id(persona: str, seq: int) -> str:
    return f'{PREFIX}{persona.upper()}-{seq:02d}'


def _patient_name(persona: str, seq: int) -> str:
    names = {
        'radiologist': 'UAT^Radiology^Patient',
        'technologist': 'UAT^Technology^Patient',
        'scheduler': 'UAT^Scheduling^Patient',
        'front-desk': 'UAT^FrontDesk^Patient',
        'biller': 'UAT^Billing^Patient',
        'ris-admin': 'UAT^Admin^Patient',
        'manager': 'UAT^Management^Patient',
    }
    return names[persona]


async def _upsert_patient(conn, persona: str, seq: int, meta=None) -> int:
    pid = _patient_id(persona, seq)
    row = await conn.fetchrow(
        """
        INSERT INTO patients (patient_id, name, birth_date, sex, meta)
        VALUES ($1, $2, $3, 'F', $4)
        ON CONFLICT (patient_id) DO UPDATE SET
            name = EXCLUDED.name, meta = EXCLUDED.meta
        RETURNING id
        """,
        pid, _patient_name(persona, seq), '19900101',
        meta or '{}',
    )
    return row['id']


async def _upsert_order(conn, persona: str, seq: int, *, status: str,
                        priority: str = 'ROUTINE',
                        prior_auth: str = 'NOT_REQUIRED') -> int:
    """ris_orders row keyed by (tenant_id, accession_number)."""
    accession = _accession(persona, seq)
    pid = _patient_id(persona, seq)
    row = await conn.fetchrow(
        """
        INSERT INTO ris_orders (tenant_id, accession_number, patient_id,
            patient_name, patient_dob, referring_physician,
            clinical_indication, priority, status, prior_auth_status, created_by)
        VALUES ('default', $1, $2, $3, '19900101', 'Lee^Kim',
            'Routine imaging', $4, $5, $6, $7)
        ON CONFLICT (tenant_id, accession_number) DO UPDATE SET
            status = EXCLUDED.status
        RETURNING id
        """,
        accession, pid, _patient_name(persona, seq), priority, status,
        prior_auth, 'seed_uat',
    )
    return row['id']


async def _upsert_exam(conn, persona: str, seq: int, *, order_id, status: str,
                       modality: str = 'CT', procedure: str = 'CT Head',
                       protocol: str = 'CT Head — Routine',
                       completed_at: str = 'NULL') -> int:
    accession = _accession(persona, seq)
    pid = _patient_id(persona, seq)
    pname = _patient_name(persona, seq)

    wle = await conn.fetchval(
        'SELECT id FROM worklist_entries WHERE accession_number = $1', accession,
    )
    if wle is None:
        wle = await conn.fetchval(
            """
            INSERT INTO worklist_entries (patient_id, patient_name,
                patient_birth_date, patient_sex, accession_number,
                requested_procedure_id, requested_procedure_desc,
                scheduled_date, scheduled_time, modality, station_ae_title,
                status, study_uid, created_by, protocol_name,
                requesting_physician, requested_procedure_priority)
            VALUES ($1, $2, '19900101', 'F', $3, '', $4, '20260825', '0900',
                $5, '', $6, '', $7, $8, 'Lee^Kim', 'routine')
            RETURNING id
            """,
            pid, pname, accession, procedure, modality,
            'performed' if status == 'completed' else 'scheduled',
            TECHNOLOGIST_ID, protocol,
        )

    existing = await conn.fetchval(
        'SELECT id FROM exams WHERE accession_number = $1', accession,
    )
    if existing:
        return existing

    return await conn.fetchval(
        f"""
        INSERT INTO exams (worklist_entry_id, patient_id, patient_name,
            patient_birth_date, patient_sex, accession_number,
            requested_procedure_desc, modality, station_ae_title, priority,
            protocol_name, status, assigned_technologist, created_by,
            referring_physician, ris_order_id, completed_at)
        VALUES ($1, $2, $3, '19900101', 'F', $4, $5, $6, '', 'routine', $7,
            $8, $9, $9, 'Lee^Kim', $10, {completed_at})
        RETURNING id
        """,
        wle, pid, pname, accession, procedure, modality, protocol, status,
        TECHNOLOGIST_ID, order_id,
    )


async def _upsert_study_files(conn, persona: str, seq: int, *, exam_id,
                              accession: str, modality: str,
                              description: str) -> None:
    """studies/series/files + replica mapping so the reading console renders."""
    pid = _patient_id(persona, seq)
    study_uid = f'1.2.826.0.1.3680043.8.498.20260825-uat-{accession.lower()}'
    series_uid = f'{study_uid}-s'
    sop_uid = f'{study_uid}-sop'

    study_id = await conn.fetchval(
        """
        INSERT INTO studies (patient_id, study_id, description,
            study_instance_uid, accession_number, study_date,
            received_instances, expected_instances, study_status)
        VALUES ($1, $2, $3, $4, $5, '20260825', 1, 1, 'complete')
        ON CONFLICT (patient_id, study_id) DO UPDATE SET
            study_status = EXCLUDED.study_status
        RETURNING id
        """,
        pid, f'UAT-ST-{accession}', description, study_uid, accession,
    )
    series_id = await conn.fetchval(
        """
        INSERT INTO series (study_id, number, modality, description,
            series_instance_uid)
        VALUES ($1, '1', $2, $3, $4)
        ON CONFLICT (study_id, number) DO UPDATE SET
            modality = EXCLUDED.modality
        RETURNING id
        """,
        study_id, modality, description, series_uid,
    )

    file_id = await conn.fetchval(
        'SELECT id FROM files WHERE sop_instance_uid = $1', sop_uid,
    )
    if file_id is None:
        dcm_path = os.path.join(
            STORAGE_DIR, pid, f'UAT-ST-{accession}', '1',
            f'{accession.lower()}.dcm',
        )
        os.makedirs(os.path.dirname(dcm_path), exist_ok=True)
        if not os.path.isfile(dcm_path):
            shutil.copyfile(FIXTURE_DCM, dcm_path)
        size = os.path.getsize(dcm_path)
        file_id = await conn.fetchval(
            """
            INSERT INTO files (patient_id, study_id, series_id, name, hash,
                sop_instance_uid, sop_class_uid, size, indexed, meta)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, false, '{}'::jsonb)
            RETURNING id
            """,
            pid, study_id, series_id, f'{accession.lower()}.dcm',
            f'uat-hash-{accession}', sop_uid, SOP_CLASS_CT_IMAGE, size,
        )
        master = await conn.fetchrow(
            'SELECT id FROM replicas WHERE master = true',
        )
        if master:
            await conn.execute(
                """
                INSERT INTO replica_files (replica_id, file_id, location,
                    status, meta)
                VALUES ($1, $2, $3, 1, '{}'::jsonb)
                ON CONFLICT (replica_id, file_id) DO UPDATE SET
                    location = EXCLUDED.location, status = EXCLUDED.status,
                    meta = EXCLUDED.meta
                """,
                master['id'], file_id, dcm_path,
            )

    await conn.execute(
        'UPDATE exams SET completed_at = now() WHERE id = $1', exam_id,
    )


async def _ensure_dicom_fixture() -> bool:
    if not os.path.isfile(FIXTURE_DCM):
        print(f'DICOM fixture not found: {FIXTURE_DCM}', file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Persona scenarios
# ---------------------------------------------------------------------------

async def seed_radiologist(conn) -> None:
    """Completed study + draft report + final signed report."""
    if not await _ensure_dicom_fixture():
        return
    order = await _upsert_order(conn, 'radiologist', 1, status='SIGNED')
    exam = await _upsert_exam(
        conn, 'radiologist', 1, order_id=order, status='completed',
        procedure='CT Head', completed_at='now()',
    )
    await _upsert_study_files(
        conn, 'radiologist', 1, exam_id=exam,
        accession=_accession('radiologist', 1),
        modality='CT', description='UAT CT head (read target)',
    )
    report = await conn.fetchrow(
        'SELECT id, status FROM reports WHERE exam_id = $1', exam,
    )
    if report is None:
        await conn.execute(
            """
            INSERT INTO reports (exam_id, status, findings, impression,
                recommendations, template_name, created_by, signed_by, signed_at)
            VALUES ($1, 'final', 'UAT demo findings.', 'UAT demo impression.',
                'Follow-up as clinically indicated.', 'CT Head', $2, $3, now())
            """,
            exam, RADIOLOGIST_ID, RADIOLOGIST_ID,
        )
    else:
        await conn.execute(
            "UPDATE reports SET status = 'final', signed_by = $2 WHERE id = $1",
            report['id'], RADIOLOGIST_ID,
        )

    # Second: draft report on a second completed exam (dashboard 'in progress').
    order2 = await _upsert_order(conn, 'radiologist', 2, status='READ')
    exam2 = await _upsert_exam(
        conn, 'radiologist', 2, order_id=order2, status='completed',
        procedure='MR Brain', modality='MR', protocol='MRI Brain — Routine',
        completed_at='now()',
    )
    await _upsert_study_files(
        conn, 'radiologist', 2, exam_id=exam2,
        accession=_accession('radiologist', 2),
        modality='MR', description='UAT MR brain (draft report target)',
    )
    if await conn.fetchval('SELECT id FROM reports WHERE exam_id = $1', exam2) is None:
        await conn.execute(
            """
            INSERT INTO reports (exam_id, status, findings, impression,
                template_name, created_by)
            VALUES ($1, 'draft', '', '', 'MR Brain', $2)
            """,
            exam2, RADIOLOGIST_ID,
        )

    print('radiologist: 2 completed exams (final report + draft report)')


async def seed_technologist(conn) -> None:
    """Worklist spread: scheduled, ready, in_progress."""
    states = [('1', 'ready'), ('2', 'in_progress'), ('3', 'scheduled')]
    for seq, status in states:
        order = await _upsert_order(
            conn, 'technologist', int(seq),
            status={'ready': 'SCHEDULED', 'in_progress': 'IN_PROGRESS',
                    'scheduled': 'ORDERED'}[status],
        )
        await _upsert_exam(
            conn, 'technologist', int(seq), order_id=order, status=status,
            procedure='CT Chest' if seq != '3' else 'CT Abdomen',
            modality='CT', protocol='CT Chest — Routine',
        )
    print('technologist: 3 worklist exams (ready / in_progress / scheduled)')


async def seed_scheduler(conn) -> None:
    """Resources + schedules + an appointment-backed scheduled order."""
    resources = [
        ('UAT CT Room', 'ROOM', 'CT', 'Floor 1'),
        ('UAT MR Room', 'ROOM', 'MR', 'Floor 1'),
    ]
    for name, rtype, modality, location in resources:
        res_id = await conn.fetchval(
            """
            INSERT INTO ris_resources (tenant_id, name, resource_type,
                modality, location, status)
            VALUES ('default', $1, $2, $3, $4, 'ACTIVE')
            ON CONFLICT (tenant_id, name) DO UPDATE SET status = 'ACTIVE'
            RETURNING id
            """,
            name, rtype, modality, location,
        )
        await conn.execute(
            """
            INSERT INTO ris_resource_schedules (tenant_id, resource_id,
                day_of_week, start_time, end_time)
            VALUES ('default', $1, 1, '08:00', '17:00'),
                   ('default', $1, 2, '08:00', '17:00'),
                   ('default', $1, 3, '08:00', '17:00'),
                   ('default', $1, 4, '08:00', '17:00'),
                   ('default', $1, 5, '08:00', '17:00')
            ON CONFLICT DO NOTHING
            """,
            res_id,
        )

    order = await _upsert_order(conn, 'scheduler', 1, status='SCHEDULED')
    res = await conn.fetchval(
        "SELECT id FROM ris_resources WHERE name = 'UAT CT Room'"
    )
    await conn.execute(
        """
        INSERT INTO ris_appointments (tenant_id, order_id, resource_id,
            patient_id, start_time, end_time, status, reason, created_by)
        VALUES ('default', $1, $2, $3, '2026-08-25 09:00', '2026-08-25 09:30',
            'SCHEDULED', '', 'seed_uat')
        ON CONFLICT DO NOTHING
        """,
        order, res, _patient_id('scheduler', 1),
    )
    print('scheduler: 2 resources + 5-day schedules + 1 appointment')


async def seed_front_desk(conn) -> None:
    """ARRIVED patient + a completed exam with a billable charge."""
    order = await _upsert_order(conn, 'front-desk', 1, status='ARRIVED')
    exam = await _upsert_exam(
        conn, 'front-desk', 1, order_id=order, status='completed',
        procedure='Chest X-Ray', modality='CR', protocol='CXR 1 View',
        completed_at='now()',
    )
    await _upsert_study_files(
        conn, 'front-desk', 1, exam_id=exam,
        accession=_accession('front-desk', 1),
        modality='CR', description='UAT CXR (billing target)',
    )
    report = await conn.fetchrow('SELECT id FROM reports WHERE exam_id = $1', exam)
    if report is None:
        report = await conn.fetchrow(
            """
            INSERT INTO reports (exam_id, status, findings, impression,
                template_name, created_by, signed_by, signed_at)
            VALUES ($1, 'final', 'UAT demo.', 'UAT demo.', 'CXR 1 View',
                $2, $2, now())
            RETURNING id
            """,
            exam, RADIOLOGIST_ID,
        )
    await conn.execute(
        """
        INSERT INTO ris_charges (tenant_id, order_id, report_id, exam_id,
            accession_number, patient_id, patient_name, cpt_code,
            cpt_description, icd10_code, charge_amount, status, created_by)
        VALUES ('default', $1, $2, $3, $4, $5, $6, '71045',
            'Chest X-ray 1 view', 'R05', 120.00, 'BILLED', 'seed_uat')
        ON CONFLICT DO NOTHING
        """,
        order, report['id'], exam, _accession('front-desk', 1),
        _patient_id('front-desk', 1), _patient_name('front-desk', 1),
    )
    print('front-desk: ARRIVED patient + completed CXR with BILLED charge')


async def seed_biller(conn) -> None:
    """Charge lifecycle spread: PENDING, BILLED, PAID, DENIED (+ claim)."""
    states = {
        1: ('PENDING', 'DRAFT'),
        2: ('PAID', 'PAID'),
        3: ('DENIED', 'DENIED'),
    }
    for seq, (charge_status, claim_status) in states.items():
        order = await _upsert_order(
            conn, 'biller', seq, status='SIGNED',
            prior_auth='APPROVED' if seq == 3 else 'NOT_REQUIRED',
        )
        exam = await _upsert_exam(
            conn, 'biller', seq, order_id=order, status='completed',
            procedure='CT Abdomen', protocol='CT Abdomen — Routine',
            completed_at='now()',
        )
        report = await conn.fetchrow(
            """
            INSERT INTO reports (exam_id, status, findings, impression,
                template_name, created_by, signed_by, signed_at)
            VALUES ($1, 'final', 'UAT demo.', 'UAT demo.', 'CT Abdomen',
                $2, $2, now())
            ON CONFLICT (exam_id) DO UPDATE SET status = 'final'
            RETURNING id
            """,
            exam, RADIOLOGIST_ID,
        )
        charge = await conn.fetchrow(
            """
            INSERT INTO ris_charges (tenant_id, order_id, report_id, exam_id,
                accession_number, patient_id, patient_name, cpt_code,
                cpt_description, icd10_code, charge_amount, status, created_by)
            VALUES ('default', $1, $2, $3, $4, $5, $6, '74176',
                'CT abdomen and pelvis w/o contrast', 'R10.9', 950.00, $7,
                'seed_uat')
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            order, report['id'], exam, _accession('biller', seq),
            _patient_id('biller', seq), _patient_name('biller', seq),
            charge_status,
        )
        if charge is None:
            charge = await conn.fetchrow(
                "SELECT id FROM ris_charges WHERE accession_number = $1 "
                "AND tenant_id = 'default'",
                _accession('biller', seq),
            )
        if seq == 3:
            await conn.execute(
                """
                INSERT INTO ris_prior_auth_requests (tenant_id, order_id,
                    procedure_code, cpt_code, payer_name, status, auth_number,
                    approved_units, approved_date, expiry_date, requested_by,
                    decided_by)
                VALUES ('default', $1, '74176', '74176', 'UAT Payer',
                    'APPROVED', 'UAT-AUTH-001', 1, '2026-08-01',
                    '2026-12-01', $2, $2)
                ON CONFLICT DO NOTHING
                """,
                order, RADIOLOGIST_ID,
            )
        await conn.execute(
            """
            INSERT INTO ris_claims (tenant_id, charge_id, claim_number,
                payer_id, payer_name, submitted_at, status, rejection_code,
                rejection_reason, paid_amount)
            VALUES ('default', $1, $2, 'UAT-PAYER', 'UAT Payer',
                CASE WHEN $3 = 'DRAFT' THEN NULL ELSE now() END, $3,
                CASE WHEN $3 = 'DENIED' THEN 'CO-16' ELSE '' END,
                CASE WHEN $3 = 'DENIED' THEN 'Claim/service lacks information' ELSE '' END,
                CASE WHEN $3 = 'PAID' THEN 950.00 ELSE NULL END)
            ON CONFLICT DO NOTHING
            """,
            charge['id'], f'UAT-CLM-{seq:02d}', claim_status,
        )
    print('biller: PENDING / PAID / DENIED charge+claim (DENIED w/ prior-auth)')


async def seed_ris_admin(conn) -> None:
    """Templates + coding map + an extra resource for admin console."""
    await conn.execute(
        """
        INSERT INTO ris_report_templates (name, modality, body_part,
            findings_template, impression_template, is_default)
        SELECT * FROM (VALUES
            ('UAT CT Chest', 'CT', 'CHEST', 'UAT findings.', 'UAT impression.', FALSE),
            ('UAT MR Brain', 'MR', 'BRAIN', 'UAT findings.', 'UAT impression.', FALSE)
        ) AS s(name, modality, body_part, findings_template, impression_template, is_default)
        WHERE NOT EXISTS (
            SELECT 1 FROM ris_report_templates t
            WHERE t.name = s.name
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO ris_coding_map (tenant_id, procedure_code, procedure_desc,
            cpt_code, cpt_description, icd10_code, icd10_description, active)
        SELECT 'default', procedure_code, procedure_desc, cpt_code,
            cpt_description, icd10_code, icd10_description, active
        FROM (VALUES
            ('CT HEAD', 'CT Head', '70450', 'CT head w/o contrast', 'R51', 'Headache', TRUE),
            ('CT ABDOMEN', 'CT Abdomen', '74176', 'CT abdomen/pelvis w/o contrast', 'R10.9', 'Abdominal pain', TRUE),
            ('CXR 1V', 'Chest X-Ray 1 view', '71045', 'Chest X-ray 1 view', 'R05', 'Cough', TRUE)
        ) AS seed(procedure_code, procedure_desc, cpt_code, cpt_description,
                  icd10_code, icd10_description, active)
        ON CONFLICT (tenant_id, procedure_code) DO UPDATE SET
            cpt_code = EXCLUDED.cpt_code,
            cpt_description = EXCLUDED.cpt_description
        """
    )
    await conn.execute(
        """
        INSERT INTO ris_resources (tenant_id, name, resource_type, modality,
            location, status)
        VALUES ('default', 'UAT US Room', 'ROOM', 'US', 'Floor 2', 'ACTIVE')
        ON CONFLICT (tenant_id, name) DO UPDATE SET status = 'ACTIVE'
        """
    )
    print('ris-admin: 2 templates + 3 coding-map rows + 1 resource')


async def seed_manager(conn) -> None:
    """Cross-status aggregate: one row in every dashboard bucket."""
    for seq, (status, charge_status) in enumerate(
            [('ready', 'PENDING'), ('in_progress', 'BILLED'),
             ('completed', 'PAID')], start=1):
        order = await _upsert_order(
            conn, 'manager', seq, status='SIGNED',
        )
        await _upsert_exam(
            conn, 'manager', seq, order_id=order, status=status,
            procedure='CT Chest', protocol='CT Chest — Routine',
            completed_at='now()' if status == 'completed' else 'NULL',
        )
        if status == 'completed':
            exam_id = await conn.fetchval(
                'SELECT id FROM exams WHERE accession_number = $1',
                _accession('manager', seq),
            )
            report = await conn.fetchrow(
                """
                INSERT INTO reports (exam_id, status, findings, impression,
                    template_name, created_by, signed_by, signed_at)
                VALUES ($1, 'final', 'UAT demo.', 'UAT demo.', 'CT Chest',
                    $2, $2, now())
                ON CONFLICT (exam_id) DO UPDATE SET status = 'final'
                RETURNING id
                """,
                exam_id, RADIOLOGIST_ID,
            )
            await conn.execute(
                """
                INSERT INTO ris_charges (tenant_id, order_id, report_id,
                    exam_id, accession_number, patient_id, patient_name,
                    cpt_code, cpt_description, icd10_code, charge_amount,
                    status, created_by)
                VALUES ('default', $1, $2, $3, $4, $5, $6, '71250',
                    'CT chest w/o contrast', 'R91', 850.00, $7, 'seed_uat')
                ON CONFLICT DO NOTHING
                """,
                order, report['id'], exam_id,
                _accession('manager', seq),
                _patient_id('manager', seq), _patient_name('manager', seq),
                charge_status,
            )
    print('manager: 3 exams across ready / in_progress / completed+PAID')


PERSONAS = {
    'radiologist': seed_radiologist,
    'technologist': seed_technologist,
    'scheduler': seed_scheduler,
    'front-desk': seed_front_desk,
    'biller': seed_biller,
    'ris-admin': seed_ris_admin,
    'manager': seed_manager,
}


async def seed(persona: str, allow_docker: bool = False) -> None:
    if is_docker() and not allow_docker:
        print('Refusing to run in a docker/QUANTUMPACS_DOCKER environment. '
              'Pass --allow-docker (or set QUANTUMPACS_SEED_ALLOW=1) to '
              'override for test environments.', file=sys.stderr)
        sys.exit(1)

    db = Database()
    await db.setup(pool_size=4)
    try:
        async with db.acquire() as conn:
            # uat-* exam rows reference ris_orders via 077 ALTER; keep the
            # script tolerant of pre-migration databases.
            await conn.execute(
                "ALTER TABLE exams ADD COLUMN IF NOT EXISTS ris_order_id UUID"
            )
            await conn.execute(
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE"
            )
            if persona == 'all':
                for name, fn in PERSONAS.items():
                    print(f'== seeding {name} ==')
                    await fn(conn)
            else:
                if persona not in PERSONAS:
                    print(f'Unknown persona {persona!r}. Choose from: '
                          f'{", ".join(["all", *PERSONAS])}', file=sys.stderr)
                    sys.exit(1)
                await PERSONAS[persona](conn)
            print('\nUAT demo data ready. See docs/uat/ for walkthroughs.')
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--persona', default='all',
        help='persona to seed (default: all): all|radiologist|technologist|'
             'scheduler|front-desk|biller|ris-admin|manager',
    )
    parser.add_argument(
        '--allow-docker', action='store_true',
        help='override the QUANTUMPACS_DOCKER guard (CI e2e only)',
    )
    args = parser.parse_args()
    allow = args.allow_docker or os.getenv('QUANTUMPACS_SEED_ALLOW') == '1'
    asyncio.run(seed(args.persona, allow_docker=allow))


if __name__ == '__main__':
    main()
