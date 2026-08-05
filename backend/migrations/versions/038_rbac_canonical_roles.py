"""Seed canonical RBAC roles per docs/reaserch/RBAC_matrix_spec.md

Revision ID: 038
Revises: 037
Create Date: 2026-08-05

Why
---
Aligns the built-in role catalog with the canonical RBAC spec
(docs/reaserch/RBAC_matrix_spec.md): 56 canonical permission codes
(§3), 24 canonical roles (§4), and the exact role→permission grants of
Matrices A/B/C (§5).

The runtime seed (db/roles.py seed_built_in_roles) upserts
api.permissions.BUILT_IN_ROLES on app startup; this migration mirrors
it so fresh databases get the canonical roles without requiring app
startup, and refreshes pre-existing slugs (radiologist, technologist,
tenant_admin, ...) whose grants change per the matrices.

Schema
------
No schema change: only roles(slug, name, permissions jsonb, built_in).
The normalized permissions / role_permissions model assumed by §2 of the
spec does not exist in this codebase; roles.permissions is a JSONB list.

Rollback
--------
Deletes the canonical role slugs that 038 introduced. Pre-existing
legacy slugs are left in place (their refreshed grants are not reverted).

References
----------
- docs/reaserch/RBAC_matrix_spec.md
"""

from alembic import op

revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


SEED_ROLES = {
    'super_admin': (
        'Super Admin',
        [
        "RESULTS_RELEASE",
        "CDS_ADMIN",
        "PATIENT_WRITE",
        "ROLE_DELETE",
        "SERVICE_KEY_READ",
        "REPORT_BUILD",
        "QA_WRITE",
        "TENANT_WRITE",
        "REGISTRATION_READ",
        "WORKLIST_WRITE",
        "PEER_REVIEW_READ",
        "FOLLOW_UP_WRITE",
        "MPI_ADMIN",
        "EXAM_WRITE",
        "STUDY_READ",
        "PEER_REVIEW_WRITE",
        "NURSING_WRITE",
        "ROLE_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "ROUTING_READ",
        "USER_ADMIN",
        "DICOMWEB_READ",
        "REPORT_WRITE",
        "ADMIN",
        "ANALYTICS_READ",
        "SYSTEM_ADMIN",
        "TENANT_ADMIN",
        "BILLING_WRITE",
        "REPLICA_READ",
        "USER_READ",
        "PRIOR_AUTH_WRITE",
        "HL7_READ",
        "STUDY_EXPORT",
        "INTERFACE_MONITOR",
        "FILE_DELETE",
        "REPLICA_WRITE",
        "STUDY_WRITE",
        "DICOMWEB_WRITE",
        "MED_VERIFY",
        "PORTAL_READ",
        "NOTE_SIGN",
        "SERVICE_KEY_WRITE",
        "EQUIPMENT_READ",
        "NURSING_READ",
        "METERING_READ",
        "BILLING_ADMIN",
        "USER_WRITE",
        "REGISTRATION_WRITE",
        "VIEWER_READ",
        "ORDER_WRITE",
        "STORAGE_ADMIN",
        "MED_ORDER_WRITE",
        "WORKLIST_READ",
        "ROUTING_WRITE",
        "FILE_READ",
        "METRICS_READ",
        "REPORT_TEMPLATE_ADMIN",
        "CARE_PLAN_WRITE",
        "QA_READ",
        "TENANT_READ",
        "HL7_WRITE",
        "HIM_WRITE",
        "AUDIT_READ",
        "INTERFACE_ADMIN",
        "RESULTS_READ",
        "ROLE_WRITE",
        "PATIENT_MERGE",
        "REPORT_SIGN",
        "QUEUE_READ",
        "USER_DELETE",
        "SERVICE_KEY_DELETE",
        "PROTOCOL_MANAGE",
        "MAR_READ",
        "MED_ORDER_READ",
        "EQUIPMENT_WRITE",
        "CRITICAL_RESULTS_WRITE",
        "FILE_WRITE",
        "MAR_WRITE",
        "SCHEDULE_READ",
        "BILLING_READ",
        "REPLICA_DELETE",
        "LOG_READ",
        "ENCOUNTER_WRITE",
        "SCHEDULE_WRITE",
        "CHART_READ",
        "CODING_WRITE",
        "LAB_SPECIMEN_WRITE",
        "PRIOR_AUTH_READ",
        "ANALYTICS_EXPORT",
        "ORDER_READ",
        "EXAM_READ",
    ]
    ),
    'admin': (
        'Administrator',
        [
        "FILE_READ",
        "FILE_WRITE",
        "FILE_DELETE",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "STUDY_READ",
        "STUDY_WRITE",
        "USER_READ",
        "USER_WRITE",
        "REPLICA_READ",
        "REPLICA_WRITE",
        "LOG_READ",
        "ROLE_READ",
        "ROLE_WRITE",
        "SERVICE_KEY_READ",
        "SERVICE_KEY_WRITE",
        "SERVICE_KEY_DELETE",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
        "EXAM_READ",
        "EXAM_WRITE",
        "REPORT_READ",
        "REPORT_WRITE",
        "REPORT_SIGN",
        "PEER_REVIEW_READ",
        "PEER_REVIEW_WRITE",
        "DICOMWEB_READ",
        "DICOMWEB_WRITE",
        "ROUTING_READ",
        "ROUTING_WRITE",
        "METRICS_READ",
        "SYSTEM_ADMIN",
        "HL7_READ",
        "HL7_WRITE",
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "QUEUE_READ",
        "BILLING_READ",
        "BILLING_WRITE",
        "BILLING_ADMIN",
        "EQUIPMENT_READ",
        "EQUIPMENT_WRITE",
        "NURSING_READ",
        "NURSING_WRITE",
        "ANALYTICS_READ",
        "ANALYTICS_EXPORT",
        "REPORT_BUILD",
        "PORTAL_READ",
        "FOLLOW_UP_WRITE",
    ]
    ),
    'technologist': (
        'Technologist',
        [
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "DICOMWEB_READ",
        "EXAM_READ",
        "EXAM_WRITE",
        "FILE_DELETE",
        "FILE_READ",
        "FILE_WRITE",
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "STUDY_WRITE",
        "VIEWER_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
    ]
    ),
    'radiologist': (
        'Radiologist',
        [
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "DICOMWEB_READ",
        "EXAM_READ",
        "FILE_READ",
        "MED_ORDER_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PEER_REVIEW_READ",
        "PEER_REVIEW_WRITE",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "REPORT_SIGN",
        "REPORT_TEMPLATE_ADMIN",
        "REPORT_WRITE",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_EXPORT",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
    ]
    ),
    'teleradiologist': (
        'Teleradiologist',
        [
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "DICOMWEB_READ",
        "EXAM_READ",
        "FILE_READ",
        "MED_ORDER_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PEER_REVIEW_READ",
        "PEER_REVIEW_WRITE",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "REPORT_SIGN",
        "REPORT_TEMPLATE_ADMIN",
        "REPORT_WRITE",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_EXPORT",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
    ]
    ),
    'qa_team': (
        'QA Team',
        [
        "FILE_READ",
        "PATIENT_READ",
        "STUDY_READ",
        "EXAM_READ",
        "QA_READ",
        "QA_WRITE",
        "PROTOCOL_MANAGE",
        "PEER_REVIEW_READ",
        "PEER_REVIEW_WRITE",
        "DICOMWEB_READ",
        "METRICS_READ",
    ]
    ),
    'physician': (
        'Physician',
        [
        "CARE_PLAN_WRITE",
        "CHART_READ",
        "DICOMWEB_READ",
        "ENCOUNTER_WRITE",
        "FILE_READ",
        "MAR_READ",
        "MED_ORDER_READ",
        "MED_ORDER_WRITE",
        "NOTE_SIGN",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'tenant_admin': (
        'Tenant Admin',
        [
        "AUDIT_READ",
        "BILLING_READ",
        "CDS_ADMIN",
        "CHART_READ",
        "FILE_DELETE",
        "FILE_READ",
        "FILE_WRITE",
        "INTERFACE_ADMIN",
        "INTERFACE_MONITOR",
        "LOG_READ",
        "METERING_READ",
        "METRICS_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "REPLICA_READ",
        "REPLICA_WRITE",
        "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN",
        "RESULTS_READ",
        "ROLE_DELETE",
        "ROLE_READ",
        "ROLE_WRITE",
        "SERVICE_KEY_DELETE",
        "SERVICE_KEY_READ",
        "SERVICE_KEY_WRITE",
        "STORAGE_ADMIN",
        "STUDY_READ",
        "STUDY_WRITE",
        "TENANT_ADMIN",
        "TENANT_READ",
        "USER_READ",
        "USER_WRITE",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'cashier': (
        'Cashier',
        [
        "BILLING_READ",
        "BILLING_WRITE",
        "CHART_READ",
        "FILE_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "REPORT_READ",
        "RESULTS_READ",
        "STUDY_READ",
    ]
    ),
    'front_desk': (
        'Front Desk',
        [
        "FILE_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "QUEUE_READ",
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "STUDY_READ",
        "WORKLIST_READ",
    ]
    ),
    'nurse': (
        'Nurse',
        [
        "CARE_PLAN_WRITE",
        "CHART_READ",
        "ENCOUNTER_WRITE",
        "EXAM_READ",
        "FILE_READ",
        "MAR_READ",
        "MAR_WRITE",
        "MED_ORDER_READ",
        "NOTE_SIGN",
        "NURSING_READ",
        "NURSING_WRITE",
        "PATIENT_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'biomedical_engineer': (
        'Biomedical Engineer',
        [
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "EQUIPMENT_READ",
        "EQUIPMENT_WRITE",
        "INTERFACE_MONITOR",
        "METERING_READ",
        "METRICS_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'service_director': (
        'Service Director',
        [
        "ANALYTICS_EXPORT",
        "ANALYTICS_READ",
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "EXAM_READ",
        "FILE_READ",
        "INTERFACE_MONITOR",
        "METERING_READ",
        "METRICS_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "QUEUE_READ",
        "REPORT_BUILD",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "WORKLIST_READ",
    ]
    ),
    'hospital_staff': (
        'Hospital Staff',
        [
        "CHART_READ",
        "FILE_READ",
        "FOLLOW_UP_WRITE",
        "MED_ORDER_READ",
        "PORTAL_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'scheduler': (
        'Scheduler',
        [
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "PRIOR_AUTH_READ",
        "PRIOR_AUTH_WRITE",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "WORKLIST_READ",
    ]
    ),
    'receptionist': (
        'Receptionist',
        [
        "ORDER_READ",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "SCHEDULE_READ",
        "WORKLIST_READ",
    ]
    ),
    'referring_physician': (
        'Referring Physician',
        [
        "CHART_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'ed_physician': (
        'ED Physician',
        [
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "ENCOUNTER_WRITE",
        "MAR_READ",
        "MED_ORDER_READ",
        "MED_ORDER_WRITE",
        "NOTE_SIGN",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'biller': (
        'Biller',
        [
        "BILLING_READ",
        "BILLING_WRITE",
        "CHART_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "RESULTS_READ",
    ]
    ),
    'department_manager': (
        'Department Manager',
        [
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "INTERFACE_MONITOR",
        "METERING_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "WORKLIST_READ",
    ]
    ),
    'radiology_admin': (
        'Radiology Admin',
        [
        "ADMIN",
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "ENCOUNTER_WRITE",
        "FILE_READ",
        "FILE_WRITE",
        "INTERFACE_ADMIN",
        "INTERFACE_MONITOR",
        "MED_ORDER_READ",
        "MED_ORDER_WRITE",
        "METERING_READ",
        "MPI_ADMIN",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_MERGE",
        "PATIENT_READ",
        "PATIENT_WRITE",
        "PRIOR_AUTH_READ",
        "PRIOR_AUTH_WRITE",
        "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN",
        "REPORT_WRITE",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "STORAGE_ADMIN",
        "STUDY_EXPORT",
        "STUDY_READ",
        "USER_READ",
        "USER_WRITE",
        "VIEWER_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
    ]
    ),
    'pacs_admin': (
        'PACS Administrator',
        [
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "CRITICAL_RESULTS_WRITE",
        "FILE_READ",
        "FILE_WRITE",
        "INTERFACE_ADMIN",
        "INTERFACE_MONITOR",
        "ORDER_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STORAGE_ADMIN",
        "STUDY_EXPORT",
        "STUDY_READ",
        "USER_READ",
        "USER_WRITE",
        "VIEWER_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
    ]
    ),
    'imaging_informatics': (
        'Imaging Informatics',
        [
        "AUDIT_READ",
        "BILLING_READ",
        "CHART_READ",
        "INTERFACE_MONITOR",
        "METERING_READ",
        "ORDER_READ",
        "PATIENT_READ",
        "REPORT_READ",
        "REPORT_TEMPLATE_ADMIN",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
        "WORKLIST_READ",
    ]
    ),
    'resident': (
        'Resident',
        [
        "CARE_PLAN_WRITE",
        "CHART_READ",
        "ENCOUNTER_WRITE",
        "MAR_READ",
        "MED_ORDER_READ",
        "MED_ORDER_WRITE",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'pharmacist': (
        'Pharmacist',
        [
        "CHART_READ",
        "MAR_READ",
        "MED_ORDER_READ",
        "MED_ORDER_WRITE",
        "MED_VERIFY",
        "PATIENT_READ",
        "RESULTS_READ",
    ]
    ),
    'lab_technician': (
        'Lab Technician',
        [
        "CHART_READ",
        "LAB_SPECIMEN_WRITE",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "RESULTS_READ",
        "RESULTS_RELEASE",
    ]
    ),
    'medical_coder': (
        'Medical Coder',
        [
        "BILLING_READ",
        "BILLING_WRITE",
        "CHART_READ",
        "CODING_WRITE",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'him_specialist': (
        'HIM Specialist',
        [
        "AUDIT_READ",
        "CHART_READ",
        "HIM_WRITE",
        "NOTE_SIGN",
        "PATIENT_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'care_coordinator': (
        'Care Coordinator',
        [
        "CARE_PLAN_WRITE",
        "CHART_READ",
        "ENCOUNTER_WRITE",
        "MED_ORDER_READ",
        "ORDER_READ",
        "ORDER_WRITE",
        "PATIENT_READ",
        "PRIOR_AUTH_READ",
        "REPORT_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "STUDY_READ",
        "VIEWER_READ",
    ]
    ),
    'emr_admin': (
        'EMR Admin',
        [
        "AUDIT_READ",
        "CDS_ADMIN",
        "INTERFACE_ADMIN",
        "INTERFACE_MONITOR",
        "METERING_READ",
        "REPORT_TEMPLATE_ADMIN",
        "ROLE_READ",
        "SERVICE_KEY_READ",
        "TENANT_READ",
        "USER_READ",
        "USER_WRITE",
    ]
    ),
    'patient': (
        'Patient',
        [
        "CHART_READ",
        "MED_ORDER_READ",
        "PORTAL_READ",
        "RESULTS_READ",
        "SCHEDULE_READ",
        "VIEWER_READ",
    ]
    ),
}


def upgrade():
    for slug, (name, permissions) in SEED_ROLES.items():
        perms_json = ", ".join(f"\"{p}\"" for p in permissions)
        op.execute(f"""
        INSERT INTO roles (slug, name, permissions, built_in, created_at, updated_at)
        VALUES (
            '{slug}',
            '{name}',
            '[{perms_json}]'::jsonb,
            TRUE,
            now(),
            now()
        )
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            permissions = EXCLUDED.permissions,
            built_in = TRUE,
            updated_at = now()
        """)


def downgrade():
    # Only the roles this migration introduced are removed; legacy slugs
    # (seeded by 008) keep their (refreshed) permission lists.
    new_slugs = [
        "teleradiologist", "scheduler", "receptionist", "referring_physician",
        "ed_physician", "biller", "medical_coder", "department_manager",
        "radiology_admin", "pacs_admin", "imaging_informatics", "resident",
        "pharmacist", "lab_technician", "him_specialist", "care_coordinator",
        "emr_admin", "patient",
    ]
    for slug in new_slugs:
        op.execute(f"DELETE FROM roles WHERE slug = '{slug}' AND built_in = TRUE")
