"""Assertions against the canonical RBAC matrix spec (docs/reaserch/RBAC_matrix_spec.md).

These are pure-data tests over api.permissions.BUILT_IN_ROLES — no DB required.
They transcribe representative rows of Matrices A/B/C (§5) and the
verification checklist (§9): every canonical permission is granted to >= 1
non-super_admin role, every role has >= 1 permission, SYSTEM_ADMIN
(super_admin) holds all permissions.
"""

from api.permissions import (
    BUILT_IN_ROLES,
    CANONICAL_PERMISSIONS,
    IMMUTABLE_ROLE_SLUGS,
    PERMISSION_KEYS,
    PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES,
    Permission,
    SUPER_ADMIN_PERMISSIONS,
)

import pytest

# The 14 slugs of the v2.16 catalog (R2-16): all canonical Matrix A/B/C roles
# plus the legacy cashier/technologist/r radiologist/teleradiologist slugs.
CANONICAL_ROLES = [
    'super_admin', 'tenant_admin', 'pacs_admin', 'emr_admin', 'patient',
    'radiologist', 'teleradiologist', 'technologist', 'cashier',
    'receptionist', 'referring_physician', 'physician', 'resident',
    'care_coordinator',
]

NON_SUPER_ADMIN = {slug for slug in BUILT_IN_ROLES if slug != 'super_admin'}


def perms(role_slug):
    return set(BUILT_IN_ROLES[role_slug])


class TestRoleCatalog:
    def test_all_canonical_roles_exist(self):
        missing = [slug for slug in CANONICAL_ROLES if slug not in BUILT_IN_ROLES]
        assert missing == []

    def test_no_dead_roles(self):
        dead = [slug for slug, perms_ in BUILT_IN_ROLES.items() if not perms_]
        assert dead == []

    def test_super_admin_holds_all_permissions(self):
        assert set(perms('super_admin')) == SUPER_ADMIN_PERMISSIONS
        assert set(perms('super_admin')) == {p.value for p in Permission}

    def test_canonical_catalog_has_56_codes(self):
        assert len(CANONICAL_PERMISSIONS) == 56
        assert len(set(CANONICAL_PERMISSIONS)) == 56

    def test_every_canonical_code_is_an_enum_member(self):
        missing = [code for code in CANONICAL_PERMISSIONS
                   if not hasattr(Permission, code)]
        assert missing == []


class TestMatrixA:
    """Matrix A — imaging roles (PACS/RIS)."""

    def test_radiologist_signs_but_technologist_cannot_read_reports(self):
        assert 'REPORT_SIGN' in perms('radiologist')
        assert 'REPORT_READ' not in perms('technologist')

    def test_teleradiologist_has_identical_grants_to_radiologist(self):
        assert perms('teleradiologist') == perms('radiologist')

    def test_cashier_writes_billing_but_radiologist_does_not(self):
        assert 'BILLING_WRITE' in perms('cashier')
        assert 'BILLING_READ' not in perms('radiologist')
        assert 'BILLING_WRITE' not in perms('radiologist')

    def test_pacs_admin_has_storage_and_interface_admin(self):
        assert 'STORAGE_ADMIN' in perms('pacs_admin')
        assert 'INTERFACE_ADMIN' in perms('pacs_admin')
        assert 'INTERFACE_MONITOR' in perms('pacs_admin')
        assert 'STUDY_EXPORT' in perms('pacs_admin')
        assert 'FILE_WRITE' in perms('pacs_admin')

    def test_pacs_admin_manages_roles_but_never_signs(self):
        # R2-16: facility admins (pacs_admin) get role management over the
        # clinical/operational built-ins and custom roles.
        assert {'ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE'} <= perms('pacs_admin')
        # pacs_admin walk F2: `_can_assign_role` needs the target's grants to
        # be a subset of the caller's, so the operational built-ins it assigns
        # (receptionist → PATIENT_WRITE, cashier → BILLING_WRITE, technologist →
        # EXAM_WRITE, ...) force those grants onto pacs_admin. Clinical-scope
        # exclusion still hides the clinical surfaces for this admin role.
        assert {'PATIENT_WRITE', 'BILLING_WRITE', 'EXAM_READ', 'EXAM_WRITE',
                'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ',
                'SCHEDULE_WRITE', 'NURSING_READ', 'NURSING_WRITE',
                'ORDER_WRITE', 'WORKLIST_WRITE', 'CRITICAL_RESULTS_WRITE'} <= perms('pacs_admin')
        # ...but never signs reports, and cannot assign clinical readers/EMR
        # writers (their grants are not a subset of pacs_admin's).
        assert 'REPORT_SIGN' not in perms('pacs_admin')
        assert 'REPORT_WRITE' not in perms('pacs_admin')
        assert not ({'CROSS_TENANT_READ', 'MED_ORDER_WRITE', 'NOTE_SIGN',
                     'MAR_READ', 'RESULTS_RELEASE', 'SYSTEM_ADMIN'} & perms('pacs_admin'))

    def test_tenant_admin_reaches_interface_surfaces(self):
        """P1-2 (tenant_admin review C2): the facility operator must actually
        reach the HL7, routing and DICOMweb surfaces their interface/storage
        grants imply — INTERFACE_ADMIN alone was a dead grant."""
        ta = perms('tenant_admin')
        assert {'HL7_READ', 'ROUTING_READ', 'DICOMWEB_READ'} <= ta
        assert {'INTERFACE_ADMIN', 'INTERFACE_MONITOR', 'STORAGE_ADMIN'} <= ta
        # FHIR stays platform policy (SYSTEM_ADMIN only).
        assert 'SYSTEM_ADMIN' not in ta
        # Still no clinical writes (Matrix C contract).
        assert not ({'PATIENT_WRITE', 'ORDER_WRITE', 'REPORT_WRITE',
                     'REPORT_SIGN', 'MAR_WRITE'} & ta)

    def test_referring_physician_is_read_only(self):
        ref = perms('referring_physician')
        assert 'REPORT_WRITE' not in ref
        assert 'REPORT_SIGN' not in ref
        assert not any(p.startswith('BILLING_') for p in ref)
        assert 'REPORT_READ' in ref and 'VIEWER_READ' in ref

    def test_receptionist_registers_and_books(self):
        rec = perms('receptionist')
        assert {'PATIENT_READ', 'PATIENT_WRITE', 'ORDER_READ',
                'SCHEDULE_READ', 'WORKLIST_READ'} <= rec
        assert 'REPORT_READ' not in rec
        # R08 front-office booking: AppointmentsHandler.post requires
        # SCHEDULE_WRITE (capacity-conflict-checked appointment creation).
        # The Matrix A row historically omitted it; the R08 receptionist
        # booking flow grants it so the front-desk UI can book patients.
        assert 'SCHEDULE_WRITE' in rec
        # R08 front-desk grants (migration 046): registration, visits and the
        # waiting queue for the front-office flow.
        assert {'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ'} <= rec


class TestMatrixB:
    """Matrix B — EMR roles."""

    def test_resident_has_no_note_sign(self):
        res = perms('resident')
        assert 'NOTE_SIGN' not in res
        assert {'ENCOUNTER_WRITE', 'MED_ORDER_WRITE', 'CARE_PLAN_WRITE',
                'MAR_READ'} <= res

    def test_resident_reads_reports_but_never_signs(self):
        """R13 radiology resident: REPORT_WRITE lets the trainee claim exams
        and draft reports; REPORT_SIGN stays with the supervising attending
        (co-sign model) so a resident can never finalize a report."""
        res = perms('resident')
        assert 'REPORT_READ' in res
        assert 'REPORT_WRITE' in res
        assert 'REPORT_SIGN' not in res

    def test_resident_reads_worklist_but_never_writes(self):
        """R13 resident review (P0-1): WORKLIST_READ read-only unlock keeps
        the Schedule Board reachable (it loads GET /api/worklist); the DICOM
        modality worklist writes stay with technologist/administrators."""
        res = perms('resident')
        assert 'WORKLIST_READ' in res
        assert 'WORKLIST_WRITE' not in res

    def test_care_coordinator_care_plans(self):
        coord = perms('care_coordinator')
        assert {'CARE_PLAN_WRITE', 'ENCOUNTER_WRITE', 'MED_ORDER_READ',
                'PRIOR_AUTH_READ'} <= coord
        assert 'MED_ORDER_WRITE' not in coord

    def test_care_coordinator_reads_schedule_and_files(self):
        """Care-coordinator review (P0-1/P1-1): read-only WORKLIST_READ +
        FILE_READ un-dead-end the Schedule Board (GET /api/worklist) and the
        always-visible Files page; write tiers stay absent."""
        coord = perms('care_coordinator')
        assert 'WORKLIST_READ' in coord
        assert 'FILE_READ' in coord
        assert 'WORKLIST_WRITE' not in coord
        assert not {'FILE_WRITE', 'FILE_DELETE'} & coord

    def test_physician_reads_schedule_and_files(self):
        """Care-coordinator review (P0-1): physician had the same schedule
        dead end (SCHEDULE_READ without WORKLIST_READ) and the same Files 403
        (the R13 comment already asserted physician holds FILE_READ)."""
        phys = perms('physician')
        assert 'WORKLIST_READ' in phys
        assert 'FILE_READ' in phys
        assert 'WORKLIST_WRITE' not in phys
        assert not {'FILE_WRITE', 'FILE_DELETE'} & phys

    def test_emr_admin_provisions_users_and_manages_roles(self):
        emr = perms('emr_admin')
        assert {'USER_READ', 'USER_WRITE', 'ROLE_READ', 'SERVICE_KEY_READ',
                'INTERFACE_ADMIN', 'CDS_ADMIN', 'REPORT_TEMPLATE_ADMIN',
                'TENANT_READ', 'METERING_READ'} <= emr
        # R2-16: emr_admin (facility admin) manages roles of the clinical/
        # operational built-ins and custom roles — no longer reserved for
        # TENANT_ADMIN/SYSTEM_ADMIN alone.
        assert {'ROLE_WRITE', 'ROLE_DELETE'} <= emr
        # EMR_ADMIN is configuration-only — no clinical data access.
        assert 'CHART_READ' not in emr
        assert 'PATIENT_READ' not in emr


class TestMatrixC:
    """Matrix C — platform roles."""

    # The clinical-write codes Matrix C deliberately excludes (§5) — the
    # R2-14 compliance assertion: tenant_admin must never hold any of them.
    CLINICAL_WRITES = {
        'PATIENT_WRITE', 'STUDY_WRITE', 'FILE_DELETE', 'ORDER_WRITE',
        'REPORT_WRITE', 'REPORT_SIGN', 'CRITICAL_RESULTS_WRITE',
        'MAR_WRITE', 'MED_ORDER_WRITE', 'MED_VERIFY', 'ENCOUNTER_WRITE',
        'NOTE_SIGN', 'RESULTS_RELEASE', 'LAB_SPECIMEN_WRITE',
        'CARE_PLAN_WRITE', 'HIM_WRITE', 'CODING_WRITE', 'BILLING_WRITE',
    }

    def test_tenant_admin_role_grants(self):
        ta = perms('tenant_admin')
        assert {'TENANT_READ', 'TENANT_ADMIN', 'METERING_READ', 'ROLE_DELETE',
                'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
                'STORAGE_ADMIN', 'BILLING_READ', 'REPORT_TEMPLATE_ADMIN',
                'CDS_ADMIN', 'AUDIT_READ', 'INTERFACE_ADMIN'} <= ta
        # Tenant admin covers platform reads, not clinical operations (§5 Matrix C).

    def test_tenant_admin_has_no_clinical_writes(self):
        """R2-14 matrix-compliance: the legacy union re-granted three clinical
        write codes the canonical Matrix C row explicitly excludes. The lock
        is a proper subset assertion, so removing any code still passes."""
        ta = perms('tenant_admin')
        assert not (self.CLINICAL_WRITES & ta)
        # tenant_admin is a platform role — no patient/study writes at all.
        assert 'PATIENT_WRITE' not in ta
        assert 'STUDY_WRITE' not in ta
        assert 'FILE_DELETE' not in ta

    def test_cashier_matches_canonical_billing_row(self):
        """R2-14 + R2-16: the kept cashier slug equals the canonical Matrix A
        billing row exactly (empty legacy union)."""
        from api.permissions import MATRIX_A_BILL
        assert perms('cashier') == MATRIX_A_BILL

    def test_technologist_has_no_clinical_writes(self):
        """R2-14: technologist keeps exam workflow codes but its legacy
        union no longer grants clinical write codes (FILE_DELETE,
        PATIENT_WRITE, STUDY_WRITE were removed)."""
        tech = perms('technologist')
        # The three over-grants removed by R2-14 are gone...
        assert not ({'FILE_DELETE', 'PATIENT_WRITE', 'STUDY_WRITE'} & tech)
        # ...while every Matrix A write the technologist legitimately holds
        # (CRITICAL_RESULTS_WRITE, WORKLIST_WRITE, FILE_WRITE) stays intact,
        # and the modality worklist surface keeps its exam/DICOM codes.
        assert {'EXAM_READ', 'EXAM_WRITE', 'DICOMWEB_READ',
                'CRITICAL_RESULTS_WRITE', 'WORKLIST_WRITE'} <= tech
        assert 'FILE_WRITE' in tech  # modality worklist write path

    def test_patient_portal_grants(self):
        patient = perms('patient')
        assert {'PORTAL_READ', 'CHART_READ', 'RESULTS_READ',
                'MED_ORDER_READ', 'SCHEDULE_READ', 'VIEWER_READ',
                'FOLLOW_UP_SELF', 'NOTIFICATIONS_SELF'} == patient


class TestDeadPermissions:
    """Spec §9: every canonical permission is granted to >= 1 non-super_admin role.

    R2-16 exception: ten codes were only ever held by removed operational
    slugs (nurse, pharmacist, lab_technician, him_specialist, medical_coder,
    radiology_admin, scheduler). They stay in the assignable catalog —
    facility admins compose them onto custom roles — so they are no longer
    built-in-granted, and the "no dead codes" assertion skips them.
    """

    # Codes whose only built-in holders were removed by the R2-16 trim.
    CUSTOM_COMPOSABLE_ONLY = {
        'RESULTS_RELEASE', 'MED_VERIFY', 'HIM_WRITE', 'MPI_ADMIN',
        # PRIOR_AUTH_WRITE removed by G2 (2026-08-25): care_coordinator now
        # holds it, so it is no longer custom-composable-only.
        'ADMIN', 'LAB_SPECIMEN_WRITE', 'CODING_WRITE',
        'MAR_WRITE', 'PATIENT_MERGE',
    }

    def test_no_dead_canonical_permissions(self):
        dead = []
        for code in CANONICAL_PERMISSIONS:
            holders = [slug for slug in NON_SUPER_ADMIN if code in perms(slug)]
            if not holders and code not in self.CUSTOM_COMPOSABLE_ONLY:
                dead.append(code)
        # The exception set must stay exact — a code that returns to a
        # built-in without leaving the exception list hides a gap.
        custom_only = {
            code for code in CANONICAL_PERMISSIONS
            if not any(code in perms(slug) for slug in NON_SUPER_ADMIN)
        }
        assert custom_only == self.CUSTOM_COMPOSABLE_ONLY
        assert dead == []


class TestRoleImmutabilityPolicy:
    """R2-16 tiers: immutable anchors, platform-admin-only slugs, editable."""

    def test_immutable_roles_exist_in_catalog(self):
        assert IMMUTABLE_ROLE_SLUGS <= set(BUILT_IN_ROLES)
        # D7: ed_physician joins the anchors — the critical-results ack
        # chain must survive facility-level role edits.
        assert IMMUTABLE_ROLE_SLUGS == {
            'super_admin', 'tenant_admin', 'pacs_admin', 'emr_admin', 'patient',
            'ed_physician',
        }

    def test_platform_admin_only_roles_exist_in_catalog(self):
        assert PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES == {'teleradiologist'}
        assert PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES <= set(BUILT_IN_ROLES)
        assert not (PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES & IMMUTABLE_ROLE_SLUGS)

    def test_exactly_nine_built_ins_are_facility_editable(self):
        editable = set(BUILT_IN_ROLES) - IMMUTABLE_ROLE_SLUGS - \
            PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES
        assert editable == {
            'radiologist', 'physician', 'referring_physician', 'resident',
            'care_coordinator', 'technologist', 'receptionist', 'cashier',
            'dept_manager',
        }

    def test_immutable_anchors_are_in_place(self):
        # The anchors must keep platform/tenant administration and the patient
        # portal safe no matter what a facility admin edits.
        for slug in ('super_admin', 'tenant_admin', 'pacs_admin', 'emr_admin',
                     'patient'):
            assert slug in IMMUTABLE_ROLE_SLUGS


class TestPermissionKeys:
    """Drift guards over PERMISSION_KEYS, the full permission catalog."""

    def test_permission_keys_are_unique_enum_values(self):
        assert len(PERMISSION_KEYS) == len(set(PERMISSION_KEYS))
        assert set(PERMISSION_KEYS) == {p.value for p in Permission}

    def test_canonical_catalog_is_a_subset_of_permission_keys(self):
        assert set(CANONICAL_PERMISSIONS) <= set(PERMISSION_KEYS)

    def test_every_group_code_is_a_valid_permission(self):
        # PERMISSION_GROUPS is hand-maintained for the roles UI; a typo here
        # silently renders a dead checkbox group. The enum is the source of
        # truth, so every group code must resolve to a member.
        from api.permissions import PERMISSION_GROUPS
        valid = set(PERMISSION_KEYS)
        bad = [
            code for group in PERMISSION_GROUPS.values() for code in group
            if code not in valid
        ]
        assert bad == []

    def test_frontend_permission_labels_do_not_drift_from_the_enum(self):
        # The frontend keeps a hand-maintained label map (api/roles.ts) for
        # the permission picker; every label key must be a backend-permitted
        # code so no UI grant can reference a permission the backend rejects.
        import re
        from pathlib import Path
        roles_ts = (
            Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'api' / 'roles.ts'
        )
        if not roles_ts.exists():
            pytest.skip('frontend source not present in this checkout')
        source = roles_ts.read_text()
        label_keys = {
            key for key in re.findall(r'^  ([A-Z][A-Z0-9_]+):', source, re.M)
            if key != 'PERMISSION_LABELS'
        }
        invalid = sorted(label_keys - set(PERMISSION_KEYS))
        assert invalid == []


class TestEdPhysicianRuntimeRole:
    """D7 (GAP_AUDIT_TDD_PIPELINE.md): migration 052 seeds ed_physician and
    critical-results recipients default to that role (migration 072), but
    the runtime catalog never carried it — it could not be assigned via the
    roles UI. It must exist at runtime with the exact seeded grants, pinned
    as an immutable anchor so facility edits can never break the
    critical-results acknowledgment chain."""

    SNAPSHOT = ['PATIENT_READ', 'ORDER_READ', 'ORDER_WRITE', 'SCHEDULE_READ',
                'WORKLIST_READ', 'REPORT_READ', 'CRITICAL_RESULTS_WRITE',
                'VIEWER_READ', 'STUDY_READ', 'CHART_READ', 'RESULTS_READ',
                'ENCOUNTER_WRITE', 'NOTE_SIGN', 'MED_ORDER_READ',
                'MED_ORDER_WRITE', 'MAR_READ']

    def test_ed_physician_in_runtime_catalog(self):
        assert 'ed_physician' in BUILT_IN_ROLES

    def test_grants_match_migration_052_snapshot(self):
        assert sorted(BUILT_IN_ROLES['ed_physician']) == sorted(self.SNAPSHOT)

    def test_holds_the_critical_ack_chain_codes(self):
        grants = set(BUILT_IN_ROLES['ed_physician'])
        assert {'CRITICAL_RESULTS_WRITE', 'REPORT_READ',
                'WORKLIST_READ'} <= grants

    def test_is_an_immutable_anchor(self):
        assert 'ed_physician' in IMMUTABLE_ROLE_SLUGS

    def test_facility_editable_set_stays_exactly_nine(self):
        editable = set(BUILT_IN_ROLES) - IMMUTABLE_ROLE_SLUGS - \
            PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES
        assert editable == {
            'radiologist', 'physician', 'referring_physician', 'resident',
            'care_coordinator', 'technologist', 'receptionist', 'cashier',
            'dept_manager',
        }
