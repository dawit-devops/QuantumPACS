"""Seed a realistic "Acme Medical Center" tenant for UAT browser testing.

Creates (idempotently):
- the `acme` tenant (slug acme)
- tenant-scoped test users (acme.super_admin, acme.cashier, acme.technologist,
  acme.radiologist, acme.care_coordinator, acme.receptionist, acme.patient)
- a procedure fee schedule (B-09) + version history
- payer contract rates (B-08) + comparison inputs
- staff time-off + coverage gaps (DM-07)
- waitlist entries (S-08), protocols (QA-09), corrective actions (QA-11)
- care plans, referrals, handoff notes, discharge checklists (CC-*)
- bookmark collections + study bookmarks (R-08)
- prior auth requests, orders, appointments, charges, claims, resources,
  worklist entries + exams + reports so each feature has data to render.

Every statement is idempotent (ON CONFLICT / DELETE-then-INSERT) so re-runs
are safe. Scope: tenant_id = 'acme' for tenant-scoped tables; clinical tables
(patients, worklist_entries, exams, reports, files) are keyed by patient_id /
accession and linked to the acme tenant where a tenant column exists.
"""
import argparse
import asyncio
import sys
from datetime import date

sys.path.insert(0, __file__.rsplit('/', 1)[0])

from config import is_docker
from db.database import Database
from db.roles import Roles
from db.users import hash_password

TEST_PASSWORD = 'Test@123456'
TENANT = 'acme'

# ---------------------------------------------------------------------------
# Seed data (B-09 fee schedule)
# ---------------------------------------------------------------------------
FEE_SCHEDULE = [
    ('71250', 'CT Chest without contrast', 350.00),
    ('71260', 'CT Chest with contrast', 450.00),
    ('72125', 'CT Head without contrast', 320.00),
    ('72141', 'MRI Head without contrast', 600.00),
    ('72148', 'MRI Lumbar Spine without contrast', 550.00),
    ('70551', 'MRI Brain without contrast', 580.00),
    ('74176', 'CT Abdomen/Pelvis without contrast', 380.00),
    ('76700', 'US Abdomen complete', 250.00),
    ('73721', 'MRI Ankle without contrast', 520.00),
    ('77067', 'Mammography screening', 200.00),
    ('78811', 'PET limited area', 950.00),
    ('78812', 'PET skull to thigh', 1200.00),
    ('78813', 'PET whole body', 1400.00),
    ('93005', 'ECG routine', 80.00),
    ('93880', 'Carotid duplex scan', 300.00),
    ('74150', 'CT Abdomen without contrast', 360.00),
    ('74160', 'CT Abdomen with contrast', 460.00),
    ('72192', 'CT Pelvis without contrast', 340.00),
    ('72156', 'MRI Cervical Spine without contrast', 540.00),
    ('74170', 'CT Abdomen/Pelvis with contrast', 480.00),
]

# (payer_id, payer_name, discount_pct)
PAYERS = [
    ('AETNA', 'Aetna', 0.15),
    ('UNITED', 'UnitedHealth', 0.18),
    ('CIGNA', 'Cigna', 0.12),
    ('BCBS', 'BlueCross', 0.10),
    ('MEDICARE', 'Medicare', 0.28),
    ('MEDICAID', 'Medicaid', 0.38),
]

# ---------------------------------------------------------------------------
# DM-07 staff time-off: (staff_id, staff_name, modality, status, start, end, reason)
# ---------------------------------------------------------------------------
TIME_OFF = [
    ('s1', 'John Smith', 'CT', 'APPROVED', '2026-09-05', '2026-09-07', 'Vacation'),
    ('s2', 'Mary Johnson', 'MR', 'APPROVED', '2026-09-10', '2026-09-12', 'Conference'),
    ('s3', 'David Brown', 'US', 'APPROVED', '2026-09-15', '2026-09-15', 'Personal day'),
    ('s4', 'Jennifer Lee', 'CT', 'REQUESTED', '2026-09-20', '2026-09-22', 'Vacation'),
    ('s5', 'Robert Taylor', 'MR', 'APPROVED', '2026-10-01', '2026-10-03', 'Medical'),
    ('s6', 'Patricia Garcia', 'DX', 'REJECTED', '2026-10-05', '2026-10-06', 'Staffing conflict'),
    ('s7', 'Michael Davis', 'NM', 'APPROVED', '2026-10-10', '2026-10-12', 'Vacation'),
    ('s8', 'Susan Miller', 'CT', 'REQUESTED', '2026-10-15', '2026-10-15', 'Personal day'),
]

# ---------------------------------------------------------------------------
# S-08 waitlist: (patient_id, patient_name, modality, priority, status, notes, resource_name)
# ---------------------------------------------------------------------------
WAITLIST = [
    ('ACMEP-001', 'Alice Wonderland', 'CT', 'STAT', 'WAITING', 'Cancelled slot 9/3 am', 'Acme CT-01'),
    ('ACMEP-002', 'Bob Builder', 'MR', 'URGENT', 'WAITING', 'Waited 5 days', 'Acme MR-01'),
    ('ACMEP-003', 'Carol Kingsley', 'US', 'ROUTINE', 'NOTIFIED', 'Called 9/1', 'Acme US-01'),
    ('ACMEP-004', 'Dan Marino', 'CT', 'URGENT', 'BOOKED', 'Converted 9/2', 'Acme CT-02'),
    ('ACMEP-005', 'Eve Adams', 'DX', 'ROUTINE', 'EXPIRED', 'No response', 'Acme DX-01'),
]

# (name, resource_type, modality, location)
RESOURCES = [
    ('Acme CT-01', 'ROOM', 'CT', 'Imaging Wing A'),
    ('Acme CT-02', 'ROOM', 'CT', 'Imaging Wing A'),
    ('Acme MR-01', 'ROOM', 'MR', 'Imaging Wing B'),
    ('Acme MR-02', 'ROOM', 'MR', 'Imaging Wing B'),
    ('Acme US-01', 'ROOM', 'US', 'Imaging Wing A'),
    ('Acme DX-01', 'ROOM', 'DX', 'Imaging Wing C'),
    ('Acme NM-01', 'ROOM', 'NM', 'Imaging Wing C'),
    ('Acme MG-01', 'ROOM', 'MG', 'Imaging Wing C'),
]

# ---------------------------------------------------------------------------
# QA-09 protocols: (name, modality, version, is_default, content)
# ---------------------------------------------------------------------------
PROTOCOLS = [
    ('CT Chest Standard', 'CT', 1, True, 'Standard chest CT protocol'),
    ('CT Chest High Res', 'CT', 1, False, 'High resolution chest CT'),
    ('CT Abdomen Standard', 'CT', 2, True, 'Standard abdomen CT with contrast'),
    ('MRI Brain Standard', 'MR', 1, True, 'Standard brain MRI'),
    ('MRI Lumbar Spine', 'MR', 1, True, 'Lumbar spine MRI without contrast'),
    ('MRI Knee', 'MR', 2, False, 'Knee MRI protocol v2'),
    ('US Abdomen Complete', 'US', 1, True, 'Complete abdominal ultrasound'),
    ('Mammography Screening', 'MG', 1, True, 'Screening mammography protocol'),
]

# ---------------------------------------------------------------------------
# QA-11 corrective actions: (title, status, priority, due, assignee, desc)
# ---------------------------------------------------------------------------
CORRECTIVE_ACTIONS = [
    ('Calibrate CT scanner #2', 'open', 'critical', '2026-09-10', 'John Smith', 'Scanner drift detected'),
    ('Update contrast protocol', 'in_progress', 'high', '2026-09-15', 'David Brown', 'New contrast guidelines'),
    ('Retrain staff on dose logging', 'open', 'medium', '2026-09-30', 'Jennifer Lee', 'Missing dose entries'),
    ('Replace MR coil', 'open', 'high', '2026-10-01', 'Robert Taylor', 'Coil signal degradation'),
    ('QA review backlog reduction', 'completed', 'medium', '2026-08-30', 'Patricia Moore', 'Backlog cleared'),
]

# ---------------------------------------------------------------------------
# CC-02 care plans: (patient_id, patient_name, title, status, tasks_json)
# ---------------------------------------------------------------------------
CARE_PLANS = [
    ('ACMEP-001', 'Alice Wonderland', 'Post-op follow-up', 'active',
     '[{"label":"Call patient","done":false},{"label":"Schedule imaging","done":false},{"label":"Review results","done":false}]'),
    ('ACMEP-002', 'Bob Builder', 'Diabetes management', 'active',
     '[{"label":"HbA1c check","done":false},{"label":"Nutrition consult","done":false},{"label":"Endocrinologist referral","done":false}]'),
    ('ACMEP-003', 'Carol Kingsley', 'Mammogram follow-up', 'completed',
     '[{"label":"Biopsy scheduled","done":true},{"label":"Results reviewed","done":true},{"label":"Patient notified","done":true}]'),
    ('ACMEP-004', 'Dan Marino', 'Cardiac workup', 'on_hold',
     '[{"label":"Stress test pending","done":false},{"label":"Cardiologist consult","done":false}]'),
    ('ACMEP-005', 'Eve Adams', 'Pre-surgery clearance', 'active',
     '[{"label":"Blood work","done":false},{"label":"Chest X-ray","done":false},{"label":"EKG","done":false},{"label":"Anesthesiology consult","done":false}]'),
]

# ---------------------------------------------------------------------------
# CC-05 referrals: (patient_id, from, to, specialty, status)
# ---------------------------------------------------------------------------
REFERRALS = [
    ('ACMEP-001', 'Dr. Smith', 'Dr. Wilson', 'Orthopedics', 'pending'),
    ('ACMEP-002', 'Dr. Chen', 'Dr. Rodriguez', 'Cardiology', 'accepted'),
    ('ACMEP-003', 'Dr. Patel', 'Dr. Kim', 'Neurology', 'completed'),
    ('ACMEP-004', 'Dr. Garcia', 'Dr. Lee', 'Oncology', 'pending'),
    ('ACMEP-005', 'Dr. Johnson', 'Dr. Brown', 'Pulmonology', 'cancelled'),
]

# ---------------------------------------------------------------------------
# CC-08 handoff notes: (patient_id, note, priority, is_read)
# ---------------------------------------------------------------------------
HANDOFF_NOTES = [
    ('ACMEP-001', 'Patient has latex allergy', 'urgent', False),
    ('ACMEP-002', 'Diabetic, needs scheduling', 'normal', False),
    ('ACMEP-003', 'Follow-up mammogram due', 'low', True),
    ('ACMEP-004', 'Cardiac history, monitor', 'high', False),
    ('ACMEP-005', 'Pre-op clearances pending', 'normal', False),
]

# ---------------------------------------------------------------------------
# CC-06 discharge checklists: (patient_id, title, status, items_json, notes)
# ---------------------------------------------------------------------------
DISCHARGE_CHECKLISTS = [
    ('ACMEP-001', 'Post-contrast monitoring', 'open',
     '[{"label":"Check vitals","done":false},{"label":"Monitor for reaction","done":false},{"label":"Document findings","done":false}]', ''),
    ('ACMEP-002', 'Diabetes discharge', 'completed',
     '[{"label":"Medication review","done":true},{"label":"Follow-up scheduled","done":true},{"label":"Diet plan provided","done":true}]', ''),
    ('ACMEP-003', 'Post-biopsy care', 'open',
     '[{"label":"Wound check","done":false},{"label":"Activity restrictions","done":false},{"label":"Emergency contact","done":false}]', ''),
]

# ---------------------------------------------------------------------------
# R-08 bookmarks
# ---------------------------------------------------------------------------
BOOKMARK_COLLECTIONS = [
    ('Interesting Chest Cases', 'Teaching cases for residents', True),
    ('My Research', 'Research study references', False),
]

# ---------------------------------------------------------------------------
# Patients for the acme tenant
# ---------------------------------------------------------------------------
PATIENTS = [
    ('ACMEP-001', 'Alice Wonderland', '1985-03-14', 'F'),
    ('ACMEP-002', 'Bob Builder', '1972-07-22', 'M'),
    ('ACMEP-003', 'Carol Kingsley', '1990-11-02', 'F'),
    ('ACMEP-004', 'Dan Marino', '1965-01-30', 'M'),
    ('ACMEP-005', 'Eve Adams', '1988-05-17', 'F'),
    ('ACMEP-006', 'Frank Castle', '1950-09-09', 'M'),
    ('ACMEP-007', 'Grace Hopper', '1945-12-09', 'F'),
    ('ACMEP-008', 'Henry Ford', '1982-04-18', 'M'),
    ('ACMEP-009', 'Iris West', '1995-08-25', 'F'),
    ('ACMEP-010', 'Jack Ryan', '1978-02-11', 'M'),
]

# (patient_id, accession, procedure_desc, modality, scheduled_date, status,
#  assigned_technologist, assigned_station_ae)
WORKLIST = [
    ('ACMEP-001', 'ACC-ACMEP-001', 'CT Chest without contrast', 'CT', '2026-09-05', 'scheduled', 'John Smith', 'CT_01'),
    ('ACMEP-001', 'ACC-ACMEP-001B', 'CT Chest with contrast', 'CT', '2026-09-06', 'scheduled', 'John Smith', 'CT_01'),
    ('ACMEP-002', 'ACC-ACMEP-002', 'MRI Brain without contrast', 'MR', '2026-09-10', 'scheduled', 'Mary Johnson', 'MR_01'),
    ('ACMEP-002', 'ACC-ACMEP-002B', 'MRI Lumbar Spine without contrast', 'MR', '2026-09-11', 'scheduled', 'Mary Johnson', 'MR_01'),
    ('ACMEP-003', 'ACC-ACMEP-003', 'US Abdomen complete', 'US', '2026-09-15', 'scheduled', 'David Brown', 'US_01'),
    ('ACMEP-004', 'ACC-ACMEP-004', 'CT Abdomen/Pelvis without contrast', 'CT', '2026-09-08', 'performed', '', 'CT_01'),
    ('ACMEP-005', 'ACC-ACMEP-005', 'Mammography screening', 'MG', '2026-09-12', 'scheduled', '', 'MG_01'),
    ('ACMEP-006', 'ACC-ACMEP-006', 'PET whole body', 'NM', '2026-09-18', 'scheduled', '', 'NM_01'),
    ('ACMEP-002', 'ACC-ACMEP-002C', 'MRI Brain without contrast', 'MR', '2026-10-02', 'scheduled', 'Robert Taylor', 'MR_01'),
    ('ACMEP-007', 'ACC-ACMEP-007', 'CT Head without contrast', 'CT', '2026-09-20', 'scheduled', 'Susan Miller', 'CT_01'),
]

# (patient_id, patient_name, procedure, cpt, charge, status, accession)
CHARGES = [
    ('ACMEP-001', 'Alice Wonderland', 'CT Chest without contrast', '71250', 350.00, 'PENDING', 'ACC-ACMEP-001'),
    ('ACMEP-002', 'Bob Builder', 'MRI Brain without contrast', '70551', 580.00, 'PENDING', 'ACC-ACMEP-002'),
    ('ACMEP-003', 'Carol Kingsley', 'US Abdomen complete', '76700', 250.00, 'PENDING', 'ACC-ACMEP-003'),
    ('ACMEP-004', 'Dan Marino', 'CT Abdomen/Pelvis without contrast', '74176', 380.00, 'BILLED', 'ACC-ACMEP-004'),
    ('ACMEP-005', 'Eve Adams', 'Mammography screening', '77067', 200.00, 'PAID', 'ACC-ACMEP-005'),
    ('ACMEP-006', 'Frank Castle', 'PET whole body', '78813', 1400.00, 'PENDING', 'ACC-ACMEP-006'),
]

# (patient_id, procedure, cpt, payer, status, auth_number)
PRIOR_AUTH = [
    ('ACMEP-001', 'MRI Brain without contrast', '70551', 'AETNA', 'APPROVED', 'AUTH-001'),
    ('ACMEP-002', 'CT Chest without contrast', '71250', 'UNITED', 'PENDING', ''),
    ('ACMEP-003', 'PET whole body', '78813', 'CIGNA', 'DENIED', ''),
    ('ACMEP-004', 'MRI Lumbar Spine without contrast', '72148', 'BCBS', 'APPROVED', 'AUTH-004'),
    ('ACMEP-005', 'CT Abdomen/Pelvis without contrast', '74176', 'MEDICARE', 'REQUIRED', ''),
    ('ACMEP-006', 'MRI Knee', '73721', 'AETNA', 'PENDING', ''),
    ('ACMEP-007', 'US Abdomen complete', '76700', 'MEDICAID', 'EXPIRED', 'AUTH-007'),
    ('ACMEP-008', 'CT Head without contrast', '72125', 'UNITED', 'NOT_REQUIRED', ''),
]

# ---------------------------------------------------------------------------
async def ensure_tenant(conn):
    """Create the acme tenant row if missing."""
    row = await conn.fetchrow("SELECT id FROM tenants WHERE slug = $1", TENANT)
    if not row:
        await conn.execute(
            """INSERT INTO tenants (name, slug, domain, db_name, db_host, db_port,
                                    db_user, db_password, status, storage_quota_bytes)
               VALUES ($1, $2, $3, $4, '127.0.0.1', 5432, $5, $6, 'active', 0)
               ON CONFLICT (slug) DO NOTHING""",
            'Acme Medical Center', TENANT, f'{TENANT}.localhost',
            TENANT, 'quantumpacs', 'quantumpacs',
        )
        print(f'  tenant {TENANT} created')
    else:
        print(f'  tenant {TENANT} exists')


async def ensure_users(conn):
    """Tenant-scoped test users for the acme tenant."""
    roles = {r['slug']: r['id'] for r in await Roles(conn).get_all()}
    wanted = ['super_admin', 'cashier', 'technologist', 'radiologist',
              'care_coordinator', 'receptionist', 'patient']
    ph = hash_password(TEST_PASSWORD)
    for slug in wanted:
        username = f'acme.{slug}'
        role_id = roles.get(slug)
        if not role_id:
            continue
        await conn.execute(
            """INSERT INTO users (username, password, admin, status, role_id, tenant, created, updated)
               VALUES ($1, $2, $3, 'active', $4, $5, now(), now())
               ON CONFLICT (username) DO UPDATE SET
                   password = EXCLUDED.password,
                   role_id = EXCLUDED.role_id,
                   status = 'active',
                   tenant = EXCLUDED.tenant,
                   updated = now()""",
            username, ph, slug == 'super_admin', role_id, TENANT,
        )
        print(f'  {username:24s} -> {slug}')


async def seed_fee_schedule(conn):
    """B-09: upsert the procedure catalog + one history row each."""
    for code, desc, price in FEE_SCHEDULE:
        await conn.execute(
            """INSERT INTO procedure_pricing_catalog (procedure_code, description, list_price, active)
               VALUES ($1, $2, $3, TRUE)
               ON CONFLICT (procedure_code) DO UPDATE SET
                   description = EXCLUDED.description,
                   list_price = EXCLUDED.list_price,
                   active = TRUE""",
            code, desc, price,
        )
        await conn.execute(
            """INSERT INTO ris_fee_schedule_history
                   (tenant_id, procedure_code, description, list_price, changed_by)
               VALUES ($1, $2, $3, $4, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, code, desc, price,
        )
    print(f'  fee schedule: {len(FEE_SCHEDULE)} procedures')


async def seed_payer_contracts(conn):
    """B-08: one contract per payer × every procedure."""
    n = 0
    for payer_id, payer_name, discount in PAYERS:
        for code, _desc, price in FEE_SCHEDULE:
            rate = round(price * (1 - discount), 2)
            await conn.execute(
                """INSERT INTO ris_payer_contracts
                       (tenant_id, payer_id, payer_name, procedure_code,
                        contracted_rate, effective_date, active, created_by)
                   VALUES ($1, $2, $3, $4, $5, '2026-01-01', TRUE, 'seed')
                   ON CONFLICT DO NOTHING""",
                TENANT, payer_id, payer_name, code, rate,
            )
            n += 1
    print(f'  payer contracts: {n}')


async def seed_time_off(conn):
    """DM-07: staff time-off requests."""
    for staff_id, name, modality, status, start, end, reason in TIME_OFF:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        await conn.execute(
            """INSERT INTO ris_staff_time_off
                   (tenant_id, staff_id, staff_name, modality, status,
                    start_date, end_date, reason, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, staff_id, name, modality, status, start_d, end_d, reason,
        )
    print(f'  time-off requests: {len(TIME_OFF)}')


async def seed_resources(conn):
    """Scheduling resources for the acme tenant (also required by waitlist)."""
    for name, rtype, modality, loc in RESOURCES:
        await conn.execute(
            """INSERT INTO ris_resources (tenant_id, name, resource_type, modality, location, status)
               VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
               ON CONFLICT (tenant_id, name) DO UPDATE SET
                   resource_type = EXCLUDED.resource_type,
                   modality = EXCLUDED.modality,
                   status = 'ACTIVE'""",
            TENANT, name, rtype, modality, loc,
        )
    print(f'  resources: {len(RESOURCES)}')


async def seed_waitlist(conn):
    """S-08: waitlist entries."""
    for pid, name, modality, priority, status, notes, res_name in WAITLIST:
        await conn.execute(
            """INSERT INTO ris_waitlist
                   (tenant_id, resource_id, patient_id, patient_name, priority,
                    status, modality, notes, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, res_name, pid, name, priority, status, modality, notes,
        )
    print(f'  waitlist: {len(WAITLIST)}')


async def seed_protocols(conn):
    """QA-09: protocol registry."""
    for name, modality, version, is_default, content in PROTOCOLS:
        await conn.execute(
            """INSERT INTO ris_protocols
                   (tenant_id, name, modality, version, is_default, content, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, name, modality, version, is_default, content,
        )
    print(f'  protocols: {len(PROTOCOLS)}')


async def seed_corrective_actions(conn):
    """QA-11: corrective actions."""
    for title, status, priority, due, assignee, desc in CORRECTIVE_ACTIONS:
        due_d = date.fromisoformat(due)
        await conn.execute(
            """INSERT INTO ris_corrective_actions
                   (tenant_id, title, description, assignee_id, status,
                    priority, due_date, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, title, desc, assignee, status, priority, due_d,
        )
    print(f'  corrective actions: {len(CORRECTIVE_ACTIONS)}')


async def seed_care_plans(conn):
    """CC-02: care plans."""
    for pid, name, title, status, tasks in CARE_PLANS:
        await conn.execute(
            """INSERT INTO care_plans
                   (patient_id, title, status, tasks, responsible_provider, tenant_id, created_by)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, 'seed')
               ON CONFLICT DO NOTHING""",
            pid, title, status, tasks, f'Dr. {name.split()[-1]}', TENANT,
        )
    print(f'  care plans: {len(CARE_PLANS)}')


async def seed_referrals(conn):
    """CC-05: referrals."""
    for pid, frm, to, spec, status in REFERRALS:
        await conn.execute(
            """INSERT INTO ris_referrals
                   (tenant_id, patient_id, from_provider, to_specialist, specialty, status, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, pid, frm, to, spec, status,
        )
    print(f'  referrals: {len(REFERRALS)}')


async def seed_handoff_notes(conn):
    """CC-08: handoff notes."""
    for pid, note, priority, is_read in HANDOFF_NOTES:
        await conn.execute(
            """INSERT INTO ris_handoff_notes
                   (tenant_id, patient_id, note, priority, is_read, created_by)
               VALUES ($1, $2, $3, $4, $5, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, pid, note, priority, is_read,
        )
    print(f'  handoff notes: {len(HANDOFF_NOTES)}')


async def seed_discharge_checklists(conn):
    """CC-06: discharge checklists."""
    for pid, title, status, items, notes in DISCHARGE_CHECKLISTS:
        await conn.execute(
            """INSERT INTO ris_discharge_checklists
                   (tenant_id, patient_id, title, status, items, notes, created_by)
               VALUES ($1, $2, $3, $4, $5::json, $6, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, pid, title, status, items, notes,
        )
    print(f'  discharge checklists: {len(DISCHARGE_CHECKLISTS)}')


async def seed_patients_and_worklist(conn):
    """Patients + worklist entries + exams so clinical pages render."""
    for pid, name, dob, sex in PATIENTS:
        await conn.execute(
            """INSERT INTO patients (patient_id, name, birth_date, sex, tenant_id)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (patient_id) DO UPDATE SET
                   name = EXCLUDED.name, birth_date = EXCLUDED.birth_date,
                   sex = EXCLUDED.sex, tenant_id = EXCLUDED.tenant_id""",
            pid, name, dob, sex, TENANT,
        )
    for pid, acc, desc, modality, sched_date, status, tech, station in WORKLIST:
        sd = date.fromisoformat(sched_date)
        await conn.execute(
            """INSERT INTO worklist_entries
                   (patient_id, patient_name, accession_number, requested_procedure_desc,
                    modality, scheduled_date, status, assigned_technologist,
                    station_ae_title, tenant_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
               ON CONFLICT (accession_number) WHERE accession_number <> '' DO UPDATE SET
                   status = EXCLUDED.status, assigned_technologist = EXCLUDED.assigned_technologist,
                   tenant_id = EXCLUDED.tenant_id""",
            pid, _name_for(pid), acc, desc, modality, sd, status, tech or '', station, TENANT,
        )
    print(f'  patients: {len(PATIENTS)}, worklist: {len(WORKLIST)}')


def _name_for(pid):
    for p in PATIENTS:
        if p[0] == pid:
            return p[1]
    return pid


async def seed_charges(conn):
    """ris_charges rows for billing pages."""
    for pid, name, desc, cpt, amount, status, acc in CHARGES:
        await conn.execute(
            """INSERT INTO ris_charges
                   (tenant_id, accession_number, patient_id, patient_name,
                    cpt_code, cpt_description, charge_amount, status, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, acc, pid, name, cpt, desc, amount, status,
        )
    print(f'  charges: {len(CHARGES)}')


async def seed_claims(conn):
    """ris_claims rows so the B-08 charge-vs-contract comparison has payers
    to match against. Charges with BILLED/PAID status get a claim bound to a
    payer that has a seeded contract (payer name must match PAYERS)."""
    for pid, name, desc, cpt, amount, status, acc in CHARGES:
        if status not in ('BILLED', 'PAID'):
            continue
        payer_id, payer_name = _payer_for(cpt)
        charge_id = await conn.fetchval(
            "SELECT id FROM ris_charges WHERE tenant_id = $1 AND accession_number = $2",
            TENANT, acc,
        )
        if not charge_id:
            continue
        await conn.execute(
            """INSERT INTO ris_claims
                   (tenant_id, charge_id, claim_number, payer_id, payer_name,
                    submitted_at, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, now(), $6, now(), now())
               ON CONFLICT DO NOTHING""",
            TENANT, charge_id, f'CLM-{acc}', payer_id, payer_name,
            'SUBMITTED' if status == 'BILLED' else 'PAID',
        )
    print('  claims: 2 (BILLED/PAID charges)')


def _payer_for(cpt):
    """Pick a payer deterministically so claims match seeded contracts."""
    idx = sum(ord(ch) for ch in cpt) % len(PAYERS)
    return PAYERS[idx][0], PAYERS[idx][1]


async def seed_prior_auth(conn):
    """ris_prior_auth_requests for prior-auth + reminders pages.
    Requires a ris_orders row (order_id FK)."""
    for pid, proc, cpt, payer, status, authnum in PRIOR_AUTH:
        # Find or create an order for this patient + procedure.
        order = await conn.fetchrow(
            "SELECT id FROM ris_orders WHERE tenant_id = $1 AND patient_id = $2 "
            "AND accession_number = $3",
            TENANT, pid, f'ACC-{pid}-PA',
        )
        if not order:
            order = await conn.fetchrow(
                """INSERT INTO ris_orders
                       (tenant_id, accession_number, patient_id, patient_name,
                        referring_physician, clinical_indication, priority,
                        status, prior_auth_status, created_by)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'seed')
                   RETURNING id""",
                TENANT, f'ACC-{pid}-PA', pid, _name_for(pid),
                'Dr. Jones', f'Clinical indication for {proc}',
                'ROUTINE', 'ORDERED', status,
            )
        await conn.execute(
            """INSERT INTO ris_prior_auth_requests
                   (tenant_id, order_id, procedure_code, cpt_code, payer_id,
                    payer_name, status, auth_number, requested_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'seed')
               ON CONFLICT DO NOTHING""",
            TENANT, order['id'], proc, cpt, payer, payer, status, authnum,
        )
    print(f'  prior-auth: {len(PRIOR_AUTH)}')


async def seed_bookmarks(conn):
    """R-08: bookmark collections + study bookmarks (sample study UIDs)."""
    # Pull a couple of real study UIDs from the default tenant so bookmarks
    # resolve to viewable studies when the user has VIEWER access.
    sample_uids = await conn.fetch(
        "SELECT study_uid FROM worklist_entries WHERE study_uid IS NOT NULL LIMIT 3")
    uids = [r['study_uid'] for r in sample_uids] or ['1.2.826.0.1.3680043.8.498.1']
    for i, (name, desc, shared) in enumerate(BOOKMARK_COLLECTIONS):
        coll = await conn.fetchrow(
            """INSERT INTO bookmark_collections
                   (tenant_id, user_id, name, description, is_shared)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id""",
            TENANT, 'acme.super_admin', name, desc, shared,
        )
        if coll:
            for uid in uids:
                await conn.execute(
                    """INSERT INTO study_bookmarks
                           (tenant_id, user_id, study_uid, study_desc, collection_id, created_at)
                       VALUES ($1, $2, $3, $4, $5::text, now())
                       ON CONFLICT DO NOTHING""",
                    TENANT, 'acme.super_admin', uid, f'Study {uid}', str(coll['id']),
                )
    print(f'  bookmark collections: {len(BOOKMARK_COLLECTIONS)}')


async def reset_seed_data(conn):
    """Idempotency guard: delete rows created by a previous seed run so
    re-running this script never accumulates duplicates. The insert paths use
    ON CONFLICT DO NOTHING on tables without unique keys, so a delete-then-
    insert is the reliable reset. Conflict-keyed tables (patients, resources,
    worklist_entries, ris_orders) are left intact."""
    # Claims are bound to seed charges (no created_by column); delete by the
    # charge ids BEFORE the charges are removed so the subquery still resolves.
    await conn.execute(
        'DELETE FROM ris_claims WHERE tenant_id = $1 '
        'AND charge_id IN (SELECT id FROM ris_charges WHERE tenant_id = $1 AND created_by = $2)',
        TENANT, 'seed')
    for tbl in (
        'ris_staff_time_off', 'ris_waitlist', 'ris_protocols',
        'ris_corrective_actions', 'care_plans', 'ris_referrals',
        'ris_handoff_notes', 'ris_discharge_checklists', 'ris_charges',
        'ris_payer_contracts',
    ):
        await conn.execute(
            f'DELETE FROM {tbl} WHERE tenant_id = $1 AND created_by = $2',
            TENANT, 'seed')
    await conn.execute(
        'DELETE FROM ris_prior_auth_requests WHERE tenant_id = $1 AND requested_by = $2',
        TENANT, 'seed')
    # Fee-schedule history tracks changed_by (no created_by column).
    await conn.execute(
        'DELETE FROM ris_fee_schedule_history WHERE tenant_id = $1 AND changed_by = $2',
        TENANT, 'seed')
    # Bookmark collections are created under the acme super_admin user.
    await conn.execute(
        'DELETE FROM study_bookmarks WHERE tenant_id = $1 AND user_id = $2',
        TENANT, 'acme.super_admin')
    await conn.execute(
        'DELETE FROM bookmark_collections WHERE tenant_id = $1 AND user_id = $2',
        TENANT, 'acme.super_admin')
    print('  reset prior seed rows')


async def seed(allow_docker: bool = False):
    if is_docker() and not allow_docker:
        print('Refusing to run in a docker/QUANTUMPACS_DOCKER environment. '
              'Pass --allow-docker to override for test environments.', file=sys.stderr)
        sys.exit(1)

    db = Database()
    await db.setup(pool_size=4)
    try:
        async with db.acquire() as conn:
            print(f'Seeding tenant "{TENANT}" (Acme Medical Center)...')
            await ensure_tenant(conn)
            await ensure_users(conn)
            await reset_seed_data(conn)
            await seed_fee_schedule(conn)
            await seed_payer_contracts(conn)
            await seed_time_off(conn)
            await seed_resources(conn)
            await seed_waitlist(conn)
            await seed_protocols(conn)
            await seed_corrective_actions(conn)
            await seed_care_plans(conn)
            await seed_referrals(conn)
            await seed_handoff_notes(conn)
            await seed_discharge_checklists(conn)
            await seed_patients_and_worklist(conn)
            await seed_charges(conn)
            await seed_claims(conn)
            await seed_prior_auth(conn)
            await seed_bookmarks(conn)
        print('\nAcme seed complete.')
        print(f'Login: username = acme.<role> (super_admin, cashier, technologist, '
              f'radiologist, care_coordinator, receptionist, patient), '
              f'password = {TEST_PASSWORD}')
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description='Seed Acme Medical Center tenant for UAT.')
    parser.add_argument('--allow-docker', action='store_true',
                        help='Allow in docker/QUANTUMPACS_DOCKER environments (test only).')
    args = parser.parse_args()
    asyncio.run(seed(args.allow_docker))


if __name__ == '__main__':
    main()
