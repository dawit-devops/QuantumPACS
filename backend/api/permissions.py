from enum import Enum


class Permission(str, Enum):
    # ---- Legacy codes (kept for backward compatibility) ----
    FILE_READ = 'FILE_READ'
    FILE_WRITE = 'FILE_WRITE'
    FILE_DELETE = 'FILE_DELETE'
    PATIENT_READ = 'PATIENT_READ'
    PATIENT_WRITE = 'PATIENT_WRITE'
    STUDY_READ = 'STUDY_READ'
    STUDY_WRITE = 'STUDY_WRITE'
    USER_READ = 'USER_READ'
    USER_WRITE = 'USER_WRITE'
    USER_DELETE = 'USER_DELETE'
    USER_ADMIN = 'USER_ADMIN'
    REPLICA_READ = 'REPLICA_READ'
    REPLICA_WRITE = 'REPLICA_WRITE'
    REPLICA_DELETE = 'REPLICA_DELETE'
    # AUDIT_READ is the canonical alias of LOG_READ (RBAC spec §6):
    # frontend code uses LOG_READ, canonical code uses AUDIT_READ — keep both.
    LOG_READ = 'LOG_READ'
    TENANT_READ = 'TENANT_READ'
    TENANT_WRITE = 'TENANT_WRITE'
    TENANT_ADMIN = 'TENANT_ADMIN'
    ROLE_READ = 'ROLE_READ'
    ROLE_WRITE = 'ROLE_WRITE'
    ROLE_DELETE = 'ROLE_DELETE'
    SERVICE_KEY_READ = 'SERVICE_KEY_READ'
    SERVICE_KEY_WRITE = 'SERVICE_KEY_WRITE'
    SERVICE_KEY_DELETE = 'SERVICE_KEY_DELETE'
    WORKLIST_READ = 'WORKLIST_READ'
    WORKLIST_WRITE = 'WORKLIST_WRITE'
    EXAM_READ = 'EXAM_READ'
    EXAM_WRITE = 'EXAM_WRITE'
    REPORT_READ = 'REPORT_READ'
    REPORT_WRITE = 'REPORT_WRITE'
    REPORT_SIGN = 'REPORT_SIGN'
    PEER_REVIEW_READ = 'PEER_REVIEW_READ'
    PEER_REVIEW_WRITE = 'PEER_REVIEW_WRITE'
    QA_READ = 'QA_READ'
    QA_WRITE = 'QA_WRITE'
    PROTOCOL_MANAGE = 'PROTOCOL_MANAGE'
    QA_ANALYTICS_READ = 'QA_ANALYTICS_READ'
    DICOMWEB_READ = 'DICOMWEB_READ'
    DICOMWEB_WRITE = 'DICOMWEB_WRITE'
    ROUTING_READ = 'ROUTING_READ'
    ROUTING_WRITE = 'ROUTING_WRITE'
    METRICS_READ = 'METRICS_READ'
    SYSTEM_ADMIN = 'SYSTEM_ADMIN'
    HL7_READ = 'HL7_READ'
    HL7_WRITE = 'HL7_WRITE'
    # R08 Front Desk
    REGISTRATION_READ = 'REGISTRATION_READ'
    REGISTRATION_WRITE = 'REGISTRATION_WRITE'
    SCHEDULE_READ = 'SCHEDULE_READ'
    SCHEDULE_WRITE = 'SCHEDULE_WRITE'
    QUEUE_READ = 'QUEUE_READ'
    # R09 Cashier
    BILLING_READ = 'BILLING_READ'
    BILLING_WRITE = 'BILLING_WRITE'
    BILLING_ADMIN = 'BILLING_ADMIN'
    # R10 Biomedical Engineer
    EQUIPMENT_READ = 'EQUIPMENT_READ'
    EQUIPMENT_WRITE = 'EQUIPMENT_WRITE'
    # R11 Nursing
    NURSING_READ = 'NURSING_READ'
    NURSING_WRITE = 'NURSING_WRITE'
    # R03 Service Director
    ANALYTICS_READ = 'ANALYTICS_READ'
    ANALYTICS_EXPORT = 'ANALYTICS_EXPORT'
    REPORT_BUILD = 'REPORT_BUILD'
    # R19 Hospital Staff
    PORTAL_READ = 'PORTAL_READ'
    FOLLOW_UP_WRITE = 'FOLLOW_UP_WRITE'
    # P-05: patient-scoped follow-up writes. Carried by the patient role so
    # patients can file/cancel their OWN follow-ups without FOLLOW_UP_WRITE
    # (which would also open scope attachment — R3-01).
    FOLLOW_UP_SELF = 'FOLLOW_UP_SELF'
    # S3 (P-04): patient-scoped notification access. The bell endpoints were
    # gated FILE_READ (a patient role grant? no), so patients could never
    # read their own notifications. NOTIFICATIONS_SELF covers the
    # user-scoped self endpoints (list/mark-read/dismiss/unread/prefs).
    NOTIFICATIONS_SELF = 'NOTIFICATIONS_SELF'
    # R2-03 Cross-tenant clinical reads (teleradiology / telemedicine) —
    # permission gate for user_tenant_grants rows: a grant only takes effect
    # when the user's role also carries this code.
    CROSS_TENANT_READ = 'CROSS_TENANT_READ'

    # ---- Canonical codes (docs/reaserch/RBAC_matrix_spec.md §3) ----
    # Platform / Identity
    ADMIN = 'ADMIN'
    AUDIT_READ = 'AUDIT_READ'  # canonical alias of LOG_READ (spec §6)
    INTERFACE_MONITOR = 'INTERFACE_MONITOR'
    INTERFACE_ADMIN = 'INTERFACE_ADMIN'
    METERING_READ = 'METERING_READ'
    # Patient / MPI
    PATIENT_MERGE = 'PATIENT_MERGE'
    MPI_ADMIN = 'MPI_ADMIN'
    # Orders & Scheduling
    ORDER_READ = 'ORDER_READ'
    ORDER_WRITE = 'ORDER_WRITE'
    PRIOR_AUTH_READ = 'PRIOR_AUTH_READ'
    PRIOR_AUTH_WRITE = 'PRIOR_AUTH_WRITE'
    # Reporting
    CRITICAL_RESULTS_WRITE = 'CRITICAL_RESULTS_WRITE'
    REPORT_TEMPLATE_ADMIN = 'REPORT_TEMPLATE_ADMIN'
    # Billing / Revenue
    CODING_WRITE = 'CODING_WRITE'
    # PACS / Imaging
    VIEWER_READ = 'VIEWER_READ'
    STUDY_EXPORT = 'STUDY_EXPORT'
    STORAGE_ADMIN = 'STORAGE_ADMIN'
    # EMR Clinical
    CHART_READ = 'CHART_READ'
    ENCOUNTER_WRITE = 'ENCOUNTER_WRITE'
    NOTE_SIGN = 'NOTE_SIGN'
    MED_ORDER_READ = 'MED_ORDER_READ'
    MED_ORDER_WRITE = 'MED_ORDER_WRITE'
    MED_VERIFY = 'MED_VERIFY'
    MAR_READ = 'MAR_READ'
    MAR_WRITE = 'MAR_WRITE'
    RESULTS_READ = 'RESULTS_READ'
    RESULTS_RELEASE = 'RESULTS_RELEASE'
    LAB_SPECIMEN_WRITE = 'LAB_SPECIMEN_WRITE'
    CARE_PLAN_WRITE = 'CARE_PLAN_WRITE'
    HIM_WRITE = 'HIM_WRITE'
    CDS_ADMIN = 'CDS_ADMIN'


# Every permission the backend knows: canonical + legacy enum members in
# declaration order. Single source of truth for code-level grants; consumers
# (role validation, UI catalogs) must not drift from it.
PERMISSION_KEYS = [p.value for p in Permission]

# Canonical permission catalog — the 56 codes from docs/reaserch/RBAC_matrix_spec.md §3.
# SYSTEM_ADMIN is the System Admin *role* code (§4), not a permission in §3;
# Matrix C grants SYSTEM_ADMIN "ALL permissions" instead.
CANONICAL_PERMISSIONS = [
    'ADMIN', 'TENANT_READ', 'TENANT_ADMIN',
    'USER_READ', 'USER_WRITE',
    'ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE',
    'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
    'AUDIT_READ', 'INTERFACE_MONITOR', 'INTERFACE_ADMIN', 'METERING_READ',
    'PATIENT_READ', 'PATIENT_WRITE', 'PATIENT_MERGE', 'MPI_ADMIN',
    'ORDER_READ', 'ORDER_WRITE',
    'SCHEDULE_READ', 'SCHEDULE_WRITE',
    'PRIOR_AUTH_READ', 'PRIOR_AUTH_WRITE',
    'WORKLIST_READ', 'WORKLIST_WRITE',
    'REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN',
    'CRITICAL_RESULTS_WRITE', 'REPORT_TEMPLATE_ADMIN',
    'BILLING_READ', 'BILLING_WRITE', 'CODING_WRITE',
    'VIEWER_READ', 'STUDY_READ', 'FILE_READ', 'FILE_WRITE',
    'STUDY_EXPORT', 'STORAGE_ADMIN',
    'CHART_READ', 'ENCOUNTER_WRITE', 'NOTE_SIGN',
    'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MED_VERIFY',
    'MAR_READ', 'MAR_WRITE',
    'RESULTS_READ', 'RESULTS_RELEASE', 'LAB_SPECIMEN_WRITE',
    'CARE_PLAN_WRITE', 'HIM_WRITE', 'CDS_ADMIN',
    'PORTAL_READ',
]

PERMISSION_GROUPS = {
    'Files': ['FILE_READ', 'FILE_WRITE', 'FILE_DELETE'],
    'Patients': ['PATIENT_READ', 'PATIENT_WRITE'],
    'Studies': ['STUDY_READ', 'STUDY_WRITE'],
    'Users': ['USER_READ', 'USER_WRITE', 'USER_DELETE', 'USER_ADMIN'],
    'Replicas': ['REPLICA_READ', 'REPLICA_WRITE', 'REPLICA_DELETE'],
    'Logs': ['LOG_READ', 'AUDIT_READ'],
    'Tenants': ['TENANT_READ', 'TENANT_WRITE', 'TENANT_ADMIN'],
    'Roles': ['ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE'],
    'Service Keys': ['SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE'],
    'Worklist': ['WORKLIST_READ', 'WORKLIST_WRITE'],
    'Exams': ['EXAM_READ', 'EXAM_WRITE'],
    'Reports': ['REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN',
                'CRITICAL_RESULTS_WRITE', 'REPORT_TEMPLATE_ADMIN'],
    'Peer Review': ['PEER_REVIEW_READ', 'PEER_REVIEW_WRITE'],
    'QA': ['QA_READ', 'QA_WRITE', 'PROTOCOL_MANAGE', 'QA_ANALYTICS_READ'],
    'DICOMweb': ['DICOMWEB_READ', 'DICOMWEB_WRITE'],
    'Routing': ['ROUTING_READ', 'ROUTING_WRITE'],
    'Metrics': ['METRICS_READ'],
    'HL7': ['HL7_READ', 'HL7_WRITE'],
    'System Admin': ['SYSTEM_ADMIN'],
    'Front Desk': ['REGISTRATION_READ', 'REGISTRATION_WRITE', 'SCHEDULE_READ', 'SCHEDULE_WRITE', 'QUEUE_READ'],
    'Billing': ['BILLING_READ', 'BILLING_WRITE', 'BILLING_ADMIN', 'CODING_WRITE'],
    'Equipment': ['EQUIPMENT_READ', 'EQUIPMENT_WRITE'],
    'Nursing': ['NURSING_READ', 'NURSING_WRITE'],
    'Analytics': ['ANALYTICS_READ', 'ANALYTICS_EXPORT', 'REPORT_BUILD'],
    'Portal': ['PORTAL_READ', 'FOLLOW_UP_WRITE'],
    'Platform': ['ADMIN'],
    'Audit & Interfaces': ['AUDIT_READ', 'INTERFACE_MONITOR', 'INTERFACE_ADMIN', 'METERING_READ'],
    'MPI': ['PATIENT_MERGE', 'MPI_ADMIN'],
    'Orders & Scheduling': ['ORDER_READ', 'ORDER_WRITE', 'SCHEDULE_READ', 'SCHEDULE_WRITE',
                            'PRIOR_AUTH_READ', 'PRIOR_AUTH_WRITE'],
    'PACS': ['VIEWER_READ', 'STUDY_READ', 'STUDY_EXPORT', 'STORAGE_ADMIN'],
    'EMR Clinical': ['CHART_READ', 'ENCOUNTER_WRITE', 'NOTE_SIGN',
                     'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MED_VERIFY',
                     'MAR_READ', 'MAR_WRITE',
                     'RESULTS_READ', 'RESULTS_RELEASE', 'LAB_SPECIMEN_WRITE',
                     'CARE_PLAN_WRITE', 'HIM_WRITE', 'CDS_ADMIN'],
}

SUPER_ADMIN_PERMISSIONS = {p.value for p in Permission}

# ---------------------------------------------------------------------------
# Canonical role→permission grants transcribed from
# docs/reaserch/RBAC_matrix_spec.md §5 (Matrices A / B / C).
# Matrix rows are the single source of truth for these sets.
# ---------------------------------------------------------------------------

# Matrix A — Imaging roles
MATRIX_A_RAD_TEL = {  # RADIOLOGIST == TELERADIOLOGIST (identical grants, §5)
    'PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    'WORKLIST_READ', 'WORKLIST_WRITE',
    'REPORT_READ', 'REPORT_WRITE', 'REPORT_SIGN', 'CRITICAL_RESULTS_WRITE',
    'REPORT_TEMPLATE_ADMIN', 'VIEWER_READ', 'STUDY_READ', 'STUDY_EXPORT',
    'CHART_READ', 'RESULTS_READ', 'MED_ORDER_READ',
    # R2-03: teleradiology reads workload from other tenants only when the
    # user holds an explicit user_tenant_grants row for that tenant.
    'CROSS_TENANT_READ',
}
MATRIX_A_TECH = {
    'PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ',
    'WORKLIST_READ', 'WORKLIST_WRITE', 'CRITICAL_RESULTS_WRITE',
    'VIEWER_READ', 'STUDY_READ', 'FILE_READ', 'FILE_WRITE',
    'CHART_READ', 'RESULTS_READ',
    # R2-14 sweep re-added: the exam console is the technologist's primary
    # surface — EXAM_READ/EXAM_WRITE belong in the canonical Matrix A row
    # (previously only in LEGACY_TECHNOLOGIST).
    'EXAM_READ', 'EXAM_WRITE',
}
MATRIX_A_RECEPT = {
    'PATIENT_READ', 'PATIENT_WRITE', 'ORDER_READ', 'SCHEDULE_READ', 'WORKLIST_READ',
    # R08 front-desk grants: registration (search/create patients), visits,
    # order intake, consents and the privacy-projected waiting queue.
    'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ',
    # SCHEDULE_WRITE: US-R08-04 has the receptionist book appointments with
    # capacity conflict detection (api/frontdesk.py AppointmentsHandler).
    # The Matrix A row historically omitted it; the R08 front-office booking
    # flow requires it, so the grant is added here to match.
    'SCHEDULE_WRITE',
}
MATRIX_A_REF = {
    'PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    'WORKLIST_READ', 'REPORT_READ', 'VIEWER_READ', 'STUDY_READ',
    'CHART_READ', 'RESULTS_READ',
}
MATRIX_A_BILL = {
    'PATIENT_READ', 'ORDER_READ', 'REPORT_READ', 'BILLING_READ', 'BILLING_WRITE',
    'CHART_READ', 'RESULTS_READ',
}
MATRIX_A_PACSADM = {
    'PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ',
    'WORKLIST_READ', 'WORKLIST_WRITE', 'REPORT_READ', 'BILLING_READ',
    'VIEWER_READ', 'STUDY_READ', 'FILE_READ', 'FILE_WRITE',
    'STUDY_EXPORT', 'STORAGE_ADMIN', 'INTERFACE_MONITOR', 'INTERFACE_ADMIN',
    'AUDIT_READ', 'CHART_READ', 'RESULTS_READ',
    'USER_READ', 'USER_WRITE', 'CRITICAL_RESULTS_WRITE', 'REPORT_TEMPLATE_ADMIN',
    # R2-16: facility admins (pacs_admin) manage roles of the clinical/
    # operational built-ins (radiologist, technologist, ...) plus custom roles.
    'ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE',
}

# Matrix B — EMR roles
MATRIX_B_PHYS = {
    'CHART_READ', 'PATIENT_READ', 'ENCOUNTER_WRITE', 'NOTE_SIGN',
    'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MAR_READ',
    'ORDER_READ', 'ORDER_WRITE', 'RESULTS_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    'REPORT_READ', 'STUDY_READ', 'VIEWER_READ', 'CARE_PLAN_WRITE',
    # Care-coordinator review (P0-1): WORKLIST_READ (read-only, no
    # WORKLIST_WRITE) unlocks the Schedule Board's day data (GET /api/worklist);
    # without it the SCHEDULE_READ route gate renders a dead end. Same pattern
    # as the R13 resident fix. FILE_READ matches the R13 comment's claim that
    # every viewer role (radiologist/technologist/physician/teleradiologist)
    # holds it — without it the always-visible Files page 403s.
    'WORKLIST_READ', 'FILE_READ',
}
MATRIX_B_RES = {
    'CHART_READ', 'PATIENT_READ', 'ENCOUNTER_WRITE',  # no NOTE_SIGN (cosign)
    'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MAR_READ',
    'ORDER_READ', 'ORDER_WRITE', 'RESULTS_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    'REPORT_READ', 'STUDY_READ', 'VIEWER_READ', 'CARE_PLAN_WRITE',
    # R13 radiology resident (supervised reading): REPORT_WRITE lets the
    # trainee claim exams and draft reports (reading console autosave,
    # Take button) — REPORT_SIGN is deliberately absent so the supervising
    # attending keeps the co-sign (drafts stay non-final until approved).
    # FILE_READ lets the Cornerstone viewport fetch DICOM pixels
    # (/api/files/{id}) and the notification bell load — every viewer role
    # (radiologist/technologist/physician/teleradiologist) holds it.
    # WORKLIST_READ (read-only, no WORKLIST_WRITE) unlocks the Schedule
    # Board's day data (GET /api/worklist); without it the SCHEDULE_READ
    # route gate renders a dead end.
    'REPORT_WRITE', 'FILE_READ', 'WORKLIST_READ',
}
MATRIX_B_COORD = {
    'CHART_READ', 'PATIENT_READ', 'ENCOUNTER_WRITE',
    'MED_ORDER_READ',  # no MED_ORDER_WRITE
    'ORDER_READ', 'ORDER_WRITE', 'RESULTS_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    # G2 (approved 2026-08-25): PRIOR_AUTH_WRITE unlocks the P0 prior-auth
    # management surface (create / submit-for-review / decide / override)
    # and reminder send+config — previously held by no staff role.
    'PRIOR_AUTH_WRITE',
    # G3 (human-approved 2026-08-25, round 5 §2.11): NURSING_READ/WRITE make
    # the coordinator the holder of the previously dead nursing grants,
    # formalizing migration 052's nurse→care_coordinator remap. Writes gate
    # the exam-linked vitals/checklist/consent/notes surfaces; reads also
    # pass via EXAM_READ on tech/rad matrices, so no other matrix changes.
    'NURSING_READ', 'NURSING_WRITE',
    'REPORT_READ', 'STUDY_READ', 'VIEWER_READ', 'CARE_PLAN_WRITE',
    # Care-coordinator review (P0-1/P1-1): WORKLIST_READ (read-only) unlocks
    # the Schedule Board's day data (GET /api/worklist) — the SCHEDULE_READ
    # route gate was a dead end without it (same defect R13 fixed for
    # resident). FILE_READ (read-only, no FILE_WRITE/DELETE) un-dead-ends the
    # always-visible Files page, matching the read-imaging stack
    # (STUDY_READ/VIEWER_READ) the role already holds.
    'WORKLIST_READ', 'FILE_READ',
}
MATRIX_B_EMRADM = {
    'AUDIT_READ',
    'USER_READ', 'USER_WRITE',
    'ROLE_READ', 'SERVICE_KEY_READ',
    # R2-16: facility admins (emr_admin) manage roles of the clinical/
    # operational built-ins (physician, resident, ...) plus custom roles;
    # ROLE_WRITE/ROLE_DELETE no longer reserved for TENANT_ADMIN alone.
    'ROLE_WRITE', 'ROLE_DELETE',
    'INTERFACE_MONITOR', 'INTERFACE_ADMIN',
    'CDS_ADMIN', 'REPORT_TEMPLATE_ADMIN', 'METERING_READ', 'TENANT_READ',
}

# Matrix C — Platform roles
# Matrix C — dept_manager (S12-34): read-only operational analytics for a
# department manager — REPORT_READ is the RIS dashboard KPI gate, BILLING_READ
# unlocks the unbilled-aging card, ANALYTICS_READ/METRICS_READ surface the
# analytics workspace, and the clinical reads let the manager open reports
# referenced from dashboards. No writes, no user/role/tenant administration.
MATRIX_C_DEPTMGR = {
    'PATIENT_READ', 'ORDER_READ', 'SCHEDULE_READ', 'PRIOR_AUTH_READ',
    'WORKLIST_READ', 'REPORT_READ', 'BILLING_READ',
    'ANALYTICS_READ', 'METRICS_READ', 'CHART_READ', 'RESULTS_READ',
    'AUDIT_READ',
    # DM-04: equipment utilization report — dept manager oversees modality
    # operations and needs equipment visibility (read-only).
    'EQUIPMENT_READ',
    # DM-07: staff schedule management — dept manager creates/edits staff
    # schedules; SCHEDULE_WRITE also enables appointment booking but the
    # dept manager is a senior role that should have full scheduling authority.
    'SCHEDULE_WRITE',
}
MATRIX_C_TENANT_ADMIN = {
    'TENANT_READ', 'TENANT_ADMIN', 'METERING_READ',
    'USER_READ', 'USER_WRITE', 'ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE',
    'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
    'AUDIT_READ', 'INTERFACE_MONITOR', 'INTERFACE_ADMIN',
    'STORAGE_ADMIN', 'BILLING_READ', 'REPORT_TEMPLATE_ADMIN', 'CDS_ADMIN',
    'PATIENT_READ', 'ORDER_READ', 'WORKLIST_READ', 'REPORT_READ',
    'STUDY_READ', 'VIEWER_READ', 'CHART_READ', 'RESULTS_READ',
    # Interface surfaces the facility operator manages (tenant_admin review
    # C2): the dashboard links and sidebar gates require these read grants;
    # INTERFACE_ADMIN/INTERFACE_MONITOR/STORAGE_ADMIN alone were dead grants
    # that unlocked no reachable UI. FHIR stays SYSTEM_ADMIN-only (platform
    # FHIR server policy).
    'HL7_READ', 'ROUTING_READ', 'DICOMWEB_READ',
    # no clinical writes (PATIENT_WRITE, ORDER_WRITE, REPORT_*, MAR_*, ...)
}
MATRIX_C_PATIENT = {
    'PORTAL_READ', 'CHART_READ', 'RESULTS_READ', 'MED_ORDER_READ',
    'SCHEDULE_READ', 'VIEWER_READ', 'FOLLOW_UP_SELF',
    'NOTIFICATIONS_SELF',
}

# ---------------------------------------------------------------------------
# Legacy grants retained so pre-existing endpoints/roles keep working; the
# canonical matrix grants are layered on top (union) for existing slugs.
# ---------------------------------------------------------------------------

LEGACY_TECHNOLOGIST = {
    'EXAM_READ', 'EXAM_WRITE', 'DICOMWEB_READ',
    # PATIENT_WRITE / STUDY_WRITE / FILE_DELETE removed (R2-14): the Matrix A
    # technologist row carries no clinical writes, and the modality worklist
    # surface needs only registrar-level read + the exam/DICOM codes above.
}
LEGACY_RADIOLOGIST = {
    'FILE_READ', 'EXAM_READ', 'PEER_REVIEW_READ', 'PEER_REVIEW_WRITE', 'DICOMWEB_READ',
}
LEGACY_PHYSICIAN = {
    'FILE_READ', 'DICOMWEB_READ',
}
LEGACY_TENANT_ADMIN = {
    'FILE_READ', 'FILE_WRITE', 'REPLICA_READ', 'REPLICA_WRITE',
    'LOG_READ', 'METRICS_READ',
    # PATIENT_WRITE / STUDY_WRITE / FILE_DELETE removed (R2-14): Matrix C
    # explicitly grants "no clinical writes" — the legacy union re-granted
    # three of them, silently exceeding the canonical role.
}
# Aligned with the canonical biller (R2-14): the legacy union granted
# PATIENT_WRITE / STUDY_READ / FILE_READ on top of MATRIX_A_BILL, giving a
# billing role more power than the Matrix A billing row. An empty set makes
# CASHIER == BILLER exactly.
LEGACY_CASHIER = set()

# RAD/TEL identical grants — teleradiologist must equal radiologist (spec §5)
RADIOLOGIST_PERMISSIONS = sorted(LEGACY_RADIOLOGIST | MATRIX_A_RAD_TEL)
TECHNOLOGIST_PERMISSIONS = sorted(LEGACY_TECHNOLOGIST | MATRIX_A_TECH)
PHYSICIAN_PERMISSIONS = sorted(LEGACY_PHYSICIAN | MATRIX_B_PHYS)
TENANT_ADMIN_PERMISSIONS = sorted(LEGACY_TENANT_ADMIN | MATRIX_C_TENANT_ADMIN)
CASHIER_PERMISSIONS = sorted(LEGACY_CASHIER | MATRIX_A_BILL)

# D7: ED physicians ack critical results — the grants mirror migration 052's
# seed snapshot exactly so upgraded DBs and fresh seeds cannot diverge.
ED_PHYSICIAN_PERMISSIONS = [
    'PATIENT_READ', 'ORDER_READ', 'ORDER_WRITE', 'SCHEDULE_READ',
    'WORKLIST_READ', 'REPORT_READ', 'CRITICAL_RESULTS_WRITE', 'VIEWER_READ',
    'STUDY_READ', 'CHART_READ', 'RESULTS_READ', 'ENCOUNTER_WRITE',
    'NOTE_SIGN', 'MED_ORDER_READ', 'MED_ORDER_WRITE', 'MAR_READ',
]


# ---------------------------------------------------------------------------
# Immutability policy for built-in roles (R2-16).
#
# Tiers (superset → subset):
#   * IMMUTABLE_ROLE_SLUGS — cannot be modified or deleted by anyone below the
#     platform admin; these anchor platform/tenant/pacs/emr administration and
#     the patient portal.
#   * PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES — editable by the platform admin
#     (super_admin, request.user.admin) only. Teleradiology coverage contracts
#     are platform policy, so facilities must not loosen these grants.
#   * All remaining built-in slugs — editable by facility admins holding
#     ROLE_WRITE (tenant_admin, pacs_admin, emr_admin). Deletion of built-in
#     roles stays blocked for every tier (R2-16).
# ---------------------------------------------------------------------------
IMMUTABLE_ROLE_SLUGS = frozenset({
    'super_admin', 'tenant_admin', 'pacs_admin', 'emr_admin', 'patient',
    # D7: the ED-physician ack chain (critical results) must survive any
    # facility-level role edit — grants stay pinned to the 052 snapshot.
    'ed_physician',
})
PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES = frozenset({'teleradiologist'})


BUILT_IN_ROLES = {
    'super_admin': list(SUPER_ADMIN_PERMISSIONS),
    'technologist': list(TECHNOLOGIST_PERMISSIONS),
    'radiologist': list(RADIOLOGIST_PERMISSIONS),
    'teleradiologist': list(RADIOLOGIST_PERMISSIONS),  # RAD == TEL (spec §5)
    'physician': list(PHYSICIAN_PERMISSIONS),
    'ed_physician': sorted(ED_PHYSICIAN_PERMISSIONS),
    'tenant_admin': list(TENANT_ADMIN_PERMISSIONS),
    'cashier': list(CASHIER_PERMISSIONS),
    # ---- Canonical roles (docs/reaserch/RBAC_matrix_spec.md §4/§5) ----
    'receptionist': sorted(MATRIX_A_RECEPT),
    'referring_physician': sorted(MATRIX_A_REF),
    'pacs_admin': sorted(MATRIX_A_PACSADM),
    'resident': sorted(MATRIX_B_RES),
    'care_coordinator': sorted(MATRIX_B_COORD),
    'emr_admin': sorted(MATRIX_B_EMRADM),
    'patient': sorted(MATRIX_C_PATIENT),
    # S12-34: department manager — read-only operational analytics (RIS
    # dashboard KPI gate REPORT_READ, unbilled aging BILLING_READ).
    'dept_manager': sorted(MATRIX_C_DEPTMGR),
}
