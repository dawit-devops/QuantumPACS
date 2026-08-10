"""Remove facility/operational roles from the built-in catalog (R2-16)

Revision ID: 052
Revises: 051
Create Date: 2026-08-11

Why
---
Round-2 audit: the 31-slug built-in catalog contains 17 facility/operational
roles that overlap the 14 kept slugs (super_admin, tenant_admin, pacs_admin,
emr_admin, radiologist, teleradiologist, physician, referring_physician,
resident, care_coordinator, technologist, receptionist, cashier, patient).
Between v2 and v3 the platform standardizes on the Matrix A/B/C slugs; the
overlapping legacy roles (`admin`, `biller`, `scheduler`, `radiology_admin`,
...) dilute auditing and force permission-set drift guards. R2-16 removes
them from the catalog and remaps any real users that still hold them.

Schema
------
No table changes. Users holding a removed role are:
  1. remapped to the closest kept role (mapping below), and their
     token_version is bumped so stale JWTs force re-auth;
  2. `test.*` fixture users (CI/e2e) holding a removed role are dropped —
     `manage seed_test_users` recreates fixtures only for kept roles;
  3. the removed role rows are deleted. `users.role_id` is the only FK into
     `roles`, so deletion order (reassign → drop fixtures → delete roles)
     keeps every constraint satisfied.

Rollback
--------
Re-inserts the 17 removed roles with the permission sets they had at v2.16.
Remapped users keep their new role — user-level remap history is not
restorable — and dropped `test.*` users are not recreated.
"""

import json

from alembic import op
from sqlalchemy import text

revision = '052'
down_revision = '051'
branch_labels = None
depends_on = None

# (removed_slug, kept_slug) — the semantic nearest match per R2-16.
REMAP = [
    ('admin', 'pacs_admin'),
    ('qa_team', 'technologist'),
    ('front_desk', 'receptionist'),
    ('nurse', 'care_coordinator'),
    ('biomedical_engineer', 'technologist'),
    ('service_director', 'pacs_admin'),
    ('hospital_staff', 'receptionist'),
    ('scheduler', 'receptionist'),
    ('ed_physician', 'physician'),
    ('biller', 'cashier'),
    ('department_manager', 'pacs_admin'),
    ('radiology_admin', 'pacs_admin'),
    ('imaging_informatics', 'emr_admin'),
    ('pharmacist', 'physician'),
    ('lab_technician', 'technologist'),
    ('medical_coder', 'cashier'),
    ('him_specialist', 'emr_admin'),
]

REMOVED_SLUGS = [old for old, _ in REMAP]
REMOVED_SLUGS_SQL = ", ".join(f"'{s}'" for s in REMOVED_SLUGS)


def upgrade():
    conn = op.get_bind()
    for removed, kept in REMAP:
        conn.execute(
            text(
                f"""
                UPDATE users u
                SET role_id = (
                    SELECT r.id FROM roles r WHERE r.slug = '{kept}'
                ),
                token_version = token_version + 1
                WHERE u.role_id = (
                    SELECT r.id FROM roles r WHERE r.slug = '{removed}'
                )
                AND u.username NOT LIKE 'test.%%'
                """
            )
        )
    conn.execute(
        text(
            f"""
            DELETE FROM users
            WHERE username LIKE 'test.%%'
            AND role_id IN (SELECT id FROM roles WHERE slug IN ({REMOVED_SLUGS_SQL}))
            """
        )
    )
    conn.execute(
        text(f"DELETE FROM roles WHERE slug IN ({REMOVED_SLUGS_SQL})")
    )


# Permission sets of the removed roles at the time of the v2.16 catalog
# (snapshot; source: backend/api/permissions.py BUILT_IN_ROLES pre-052).
SNAPSHOT_PERMISSIONS = {
    'admin': ['FILE_READ', 'FILE_WRITE', 'FILE_DELETE', 'PATIENT_READ', 'PATIENT_WRITE',
              'STUDY_READ', 'STUDY_WRITE', 'USER_READ', 'USER_WRITE', 'REPLICA_READ',
              'REPLICA_WRITE', 'LOG_READ', 'ROLE_READ', 'ROLE_WRITE', 'SERVICE_KEY_READ',
              'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE', 'WORKLIST_READ', 'WORKLIST_WRITE',
              'EXAM_READ', 'EXAM_WRITE', 'REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN',
              'PEER_REVIEW_READ', 'PEER_REVIEW_WRITE', 'DICOMWEB_READ', 'DICOMWEB_WRITE',
              'ROUTING_READ', 'ROUTING_WRITE', 'METRICS_READ', 'SYSTEM_ADMIN', 'HL7_READ',
              'HL7_WRITE', 'REGISTRATION_READ', 'REGISTRATION_WRITE', 'SCHEDULE_READ',
              'SCHEDULE_WRITE', 'QUEUE_READ', 'BILLING_READ', 'BILLING_WRITE',
              'BILLING_ADMIN', 'EQUIPMENT_READ', 'EQUIPMENT_WRITE', 'NURSING_READ',
              'NURSING_WRITE', 'ANALYTICS_READ', 'ANALYTICS_EXPORT', 'REPORT_BUILD',
              'PORTAL_READ', 'FOLLOW_UP_WRITE'],
    'qa_team': ['FILE_READ', 'PATIENT_READ', 'STUDY_READ', 'EXAM_READ', 'QA_READ',
                'QA_WRITE', 'PROTOCOL_MANAGE', 'PEER_REVIEW_READ', 'PEER_REVIEW_WRITE',
                'DICOMWEB_READ', 'METRICS_READ'],
    'front_desk': ['PATIENT_READ', 'PATIENT_WRITE', 'ORDER_READ', 'SCHEDULE_READ',
                   'SCHEDULE_WRITE', 'WORKLIST_READ', 'REGISTRATION_READ',
                   'REGISTRATION_WRITE', 'QUEUE_READ', 'FILE_READ', 'STUDY_READ'],
    'nurse': ['CHART_READ', 'PATIENT_READ', 'ENCOUNTER_WRITE', 'NOTE_SIGN', 'MED_ORDER_READ',
              'MAR_READ', 'MAR_WRITE', 'RESULTS_READ', 'SCHEDULE_READ', 'REPORT_READ',
              'STUDY_READ', 'VIEWER_READ', 'CARE_PLAN_WRITE', 'FILE_READ', 'EXAM_READ',
              'WORKLIST_READ', 'NURSING_READ', 'NURSING_WRITE'],
    'biomedical_engineer': ['PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'WORKLIST_READ',
                            'REPORT_READ', 'REPORT_TEMPLATE_ADMIN', 'BILLING_READ',
                            'VIEWER_READ', 'STUDY_READ', 'INTERFACE_MONITOR', 'AUDIT_READ',
                            'METERING_READ', 'CHART_READ', 'RESULTS_READ', 'EQUIPMENT_READ',
                            'EQUIPMENT_WRITE', 'METRICS_READ'],
    'service_director': ['PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'WORKLIST_READ',
                         'REPORT_READ', 'BILLING_READ', 'STUDY_READ', 'INTERFACE_MONITOR',
                         'AUDIT_READ', 'METERING_READ', 'CHART_READ', 'RESULTS_READ',
                         'FILE_READ', 'EXAM_READ', 'ANALYTICS_READ', 'ANALYTICS_EXPORT',
                         'REPORT_BUILD', 'QUEUE_READ', 'METRICS_READ'],
    'hospital_staff': ['PORTAL_READ', 'CHART_READ', 'RESULTS_READ', 'MED_ORDER_READ',
                       'SCHEDULE_READ', 'VIEWER_READ', 'FILE_READ', 'STUDY_READ',
                       'FOLLOW_UP_WRITE'],
    'scheduler': ['PATIENT_READ', 'PATIENT_WRITE', 'ORDER_READ', 'SCHEDULE_READ',
                  'SCHEDULE_WRITE', 'PRIOR_AUTH_READ', 'PRIOR_AUTH_WRITE', 'WORKLIST_READ',
                  'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ'],
    'ed_physician': ['PATIENT_READ', 'ORDER_READ', 'ORDER_WRITE', 'SCHEDULE_READ',
                     'WORKLIST_READ', 'REPORT_READ', 'CRITICAL_RESULTS_WRITE', 'VIEWER_READ',
                     'STUDY_READ', 'CHART_READ', 'RESULTS_READ', 'ENCOUNTER_WRITE',
                     'NOTE_SIGN', 'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MAR_READ'],
    'biller': ['PATIENT_READ', 'ORDER_READ', 'REPORT_READ', 'BILLING_READ', 'BILLING_WRITE',
               'CHART_READ', 'RESULTS_READ'],
    'department_manager': ['PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'WORKLIST_READ',
                           'REPORT_READ', 'BILLING_READ', 'STUDY_READ', 'INTERFACE_MONITOR',
                           'AUDIT_READ', 'METERING_READ', 'CHART_READ', 'RESULTS_READ'],
    'radiology_admin': ['PATIENT_READ', 'PATIENT_WRITE', 'PATIENT_MERGE', 'MPI_ADMIN',
                        'ORDER_READ', 'ORDER_WRITE', 'SCHEDULE_READ', 'SCHEDULE_WRITE',
                        'PRIOR_AUTH_READ', 'PRIOR_AUTH_WRITE', 'WORKLIST_READ',
                        'WORKLIST_WRITE', 'REPORT_READ', 'REPORT_WRITE',
                        'CRITICAL_RESULTS_WRITE', 'REPORT_TEMPLATE_ADMIN', 'BILLING_READ',
                        'VIEWER_READ', 'STUDY_READ', 'FILE_READ', 'FILE_WRITE',
                        'STUDY_EXPORT', 'STORAGE_ADMIN', 'INTERFACE_MONITOR',
                        'INTERFACE_ADMIN', 'AUDIT_READ', 'METERING_READ', 'CHART_READ',
                        'RESULTS_READ', 'USER_READ', 'USER_WRITE', 'ENCOUNTER_WRITE',
                        'MED_ORDER_READ', 'MED_ORDER_WRITE', 'ADMIN'],
    'imaging_informatics': ['PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'WORKLIST_READ',
                            'REPORT_READ', 'REPORT_TEMPLATE_ADMIN', 'BILLING_READ',
                            'VIEWER_READ', 'STUDY_READ', 'INTERFACE_MONITOR', 'AUDIT_READ',
                            'METERING_READ', 'CHART_READ', 'RESULTS_READ'],
    'pharmacist': ['CHART_READ', 'PATIENT_READ', 'MED_ORDER_READ', 'MED_ORDER_WRITE',
                   'MED_VERIFY', 'MAR_READ', 'RESULTS_READ'],
    'lab_technician': ['CHART_READ', 'PATIENT_READ', 'ORDER_READ', 'ORDER_WRITE',
                       'RESULTS_READ', 'RESULTS_RELEASE', 'LAB_SPECIMEN_WRITE'],
    'medical_coder': ['CHART_READ', 'PATIENT_READ', 'ORDER_READ', 'ORDER_WRITE',
                      'RESULTS_READ', 'PRIOR_AUTH_READ', 'REPORT_READ', 'STUDY_READ',
                      'VIEWER_READ', 'CODING_WRITE', 'BILLING_READ', 'BILLING_WRITE'],
    'him_specialist': ['CHART_READ', 'PATIENT_READ', 'NOTE_SIGN', 'RESULTS_READ',
                       'REPORT_READ', 'STUDY_READ', 'VIEWER_READ', 'HIM_WRITE',
                       'AUDIT_READ'],
}

SNAPSHOT_NAMES = {
    'admin': 'Administrator',
    'qa_team': 'QA Team',
    'front_desk': 'Front Desk',
    'nurse': 'Nurse',
    'biomedical_engineer': 'Biomedical Engineer',
    'service_director': 'Service Director',
    'hospital_staff': 'Hospital Staff',
    'scheduler': 'Scheduler',
    'ed_physician': 'ED Physician',
    'biller': 'Biller',
    'department_manager': 'Department Manager',
    'radiology_admin': 'Radiology Admin',
    'imaging_informatics': 'Imaging Informatics',
    'pharmacist': 'Pharmacist',
    'lab_technician': 'Lab Technician',
    'medical_coder': 'Medical Coder',
    'him_specialist': 'HIM Specialist',
}


def downgrade():
    conn = op.get_bind()
    for slug in REMOVED_SLUGS:
        perms = SNAPSHOT_PERMISSIONS[slug]
        conn.execute(
            text(
                """
                INSERT INTO roles (slug, name, permissions, built_in, created_at, updated_at)
                VALUES (%s, %s, %s::jsonb, TRUE, now(), now())
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            (slug, SNAPSHOT_NAMES[slug], json.dumps(perms)),
        )