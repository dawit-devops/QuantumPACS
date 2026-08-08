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
    PERMISSION_KEYS,
    Permission,
    SUPER_ADMIN_PERMISSIONS,
)

import pytest

CANONICAL_ROLES = [
    'super_admin', 'tenant_admin', 'patient',
    'radiologist', 'teleradiologist', 'technologist',
    'scheduler', 'receptionist', 'referring_physician', 'ed_physician',
    'biller', 'medical_coder', 'department_manager',
    'radiology_admin', 'pacs_admin', 'imaging_informatics',
    'physician', 'resident', 'nurse', 'pharmacist', 'lab_technician',
    'him_specialist', 'care_coordinator', 'emr_admin',
]

NON_SUPER_ADMIN = {slug for slug in BUILT_IN_ROLES if slug != 'super_admin'}


def perms(role_slug):
    return set(BUILT_IN_ROLES[role_slug])


class TestRoleCatalog:
    def test_all_24_canonical_roles_exist(self):
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

    def test_biller_writes_billing_but_radiologist_does_not(self):
        assert 'BILLING_WRITE' in perms('biller')
        assert 'BILLING_READ' not in perms('radiologist')
        assert 'BILLING_WRITE' not in perms('radiologist')

    def test_pacs_admin_has_storage_and_interface_admin(self):
        assert 'STORAGE_ADMIN' in perms('pacs_admin')
        assert 'INTERFACE_ADMIN' in perms('pacs_admin')
        assert 'INTERFACE_MONITOR' in perms('pacs_admin')
        assert 'STUDY_EXPORT' in perms('pacs_admin')
        assert 'FILE_WRITE' in perms('pacs_admin')

    def test_referring_physician_is_read_only(self):
        ref = perms('referring_physician')
        assert 'REPORT_WRITE' not in ref
        assert 'REPORT_SIGN' not in ref
        assert not any(p.startswith('BILLING_') for p in ref)
        assert 'REPORT_READ' in ref and 'VIEWER_READ' in ref

    def test_radiology_admin_ops_but_no_report_sign(self):
        ra = perms('radiology_admin')
        assert 'REPORT_WRITE' in ra
        assert 'REPORT_SIGN' not in ra
        assert 'PATIENT_MERGE' in ra and 'MPI_ADMIN' in ra
        assert 'ADMIN' in ra
        assert 'SCHEDULE_WRITE' in ra and 'PRIOR_AUTH_WRITE' in ra

    def test_scheduler_schedules_and_prior_auth(self):
        sch = perms('scheduler')
        assert {'SCHEDULE_READ', 'SCHEDULE_WRITE', 'PRIOR_AUTH_READ',
                'PRIOR_AUTH_WRITE', 'PATIENT_WRITE'} <= sch
        assert 'REPORT_READ' not in sch

    def test_receptionist_registers_only(self):
        rec = perms('receptionist')
        assert {'PATIENT_READ', 'PATIENT_WRITE', 'ORDER_READ',
                'SCHEDULE_READ', 'WORKLIST_READ'} <= rec
        assert 'REPORT_READ' not in rec
        assert 'SCHEDULE_WRITE' not in rec

    def test_ed_physician_full_scope(self):
        ed = perms('ed_physician')
        assert {'CRITICAL_RESULTS_WRITE', 'ENCOUNTER_WRITE', 'NOTE_SIGN',
                'MED_ORDER_READ', 'MED_ORDER_WRITE', 'ORDER_WRITE',
                'MAR_READ'} <= ed
        assert 'REPORT_SIGN' not in ed

    def test_department_manager_analytics(self):
        dm = perms('department_manager')
        assert {'AUDIT_READ', 'METERING_READ', 'INTERFACE_MONITOR',
                'BILLING_READ', 'STUDY_READ'} <= dm
        assert 'BILLING_WRITE' not in dm

    def test_imaging_informatics_interoperability(self):
        info = perms('imaging_informatics')
        assert {'INTERFACE_MONITOR', 'AUDIT_READ', 'METERING_READ',
                'REPORT_TEMPLATE_ADMIN', 'REPORT_READ'} <= info
        assert 'REPORT_WRITE' not in info
        assert 'STORAGE_ADMIN' not in info
        assert 'FILE_READ' not in info


class TestMatrixB:
    """Matrix B — EMR roles."""

    def test_resident_has_no_note_sign(self):
        res = perms('resident')
        assert 'NOTE_SIGN' not in res
        assert {'ENCOUNTER_WRITE', 'MED_ORDER_WRITE', 'CARE_PLAN_WRITE',
                'MAR_READ'} <= res

    def test_nurse_administers_meds(self):
        nurse = perms('nurse')
        assert {'MAR_READ', 'MAR_WRITE', 'NOTE_SIGN', 'MED_ORDER_READ',
                'ENCOUNTER_WRITE'} <= nurse
        assert 'MED_ORDER_WRITE' not in nurse

    def test_pharmacist_verifies_meds(self):
        pharm = perms('pharmacist')
        assert {'MED_VERIFY', 'MED_ORDER_READ', 'MED_ORDER_WRITE',
                'MAR_READ'} <= pharm
        assert 'MAR_WRITE' not in pharm
        assert 'REPORT_READ' not in pharm

    def test_lab_technician_releases_results(self):
        lab = perms('lab_technician')
        assert {'RESULTS_READ', 'RESULTS_RELEASE', 'LAB_SPECIMEN_WRITE',
                'ORDER_READ', 'ORDER_WRITE'} <= lab
        assert 'MAR_READ' not in lab

    def test_medical_coder_codes_billing(self):
        coder = perms('medical_coder')
        assert {'CODING_WRITE', 'BILLING_READ', 'BILLING_WRITE'} <= coder
        assert 'HIM_WRITE' not in coder

    def test_him_specialist_amend_and_audit(self):
        him = perms('him_specialist')
        assert {'HIM_WRITE', 'AUDIT_READ', 'NOTE_SIGN', 'CHART_READ'} <= him
        assert 'BILLING_WRITE' not in him

    def test_care_coordinator_care_plans(self):
        coord = perms('care_coordinator')
        assert {'CARE_PLAN_WRITE', 'ENCOUNTER_WRITE', 'MED_ORDER_READ',
                'PRIOR_AUTH_READ'} <= coord
        assert 'MED_ORDER_WRITE' not in coord

    def test_emr_admin_provisions_users_without_clinical_access(self):
        emr = perms('emr_admin')
        assert {'USER_READ', 'USER_WRITE', 'ROLE_READ', 'SERVICE_KEY_READ',
                'INTERFACE_ADMIN', 'CDS_ADMIN', 'REPORT_TEMPLATE_ADMIN',
                'TENANT_READ', 'METERING_READ'} <= emr
        # Role creation/deletion is reserved for TENANT_ADMIN/SYSTEM_ADMIN (§5).
        assert 'ROLE_WRITE' not in emr
        assert 'ROLE_DELETE' not in emr
        # EMR_ADMIN is configuration-only — no clinical data access.
        assert 'CHART_READ' not in emr
        assert 'PATIENT_READ' not in emr


class TestMatrixC:
    """Matrix C — platform roles."""

    def test_tenant_admin_role_grants(self):
        ta = perms('tenant_admin')
        assert {'TENANT_READ', 'TENANT_ADMIN', 'METERING_READ', 'ROLE_DELETE',
                'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
                'STORAGE_ADMIN', 'BILLING_READ', 'REPORT_TEMPLATE_ADMIN',
                'CDS_ADMIN', 'AUDIT_READ', 'INTERFACE_ADMIN'} <= ta
        # Tenant admin covers platform reads, not clinical operations (§5 Matrix C).

    def test_patient_portal_grants(self):
        patient = perms('patient')
        assert {'PORTAL_READ', 'CHART_READ', 'RESULTS_READ',
                'MED_ORDER_READ', 'SCHEDULE_READ', 'VIEWER_READ'} == patient


class TestDeadPermissions:
    """Spec §9: every canonical permission is granted to >= 1 non-super_admin role."""

    def test_no_dead_canonical_permissions(self):
        dead = []
        for code in CANONICAL_PERMISSIONS:
            holders = [slug for slug in NON_SUPER_ADMIN if code in perms(slug)]
            if not holders:
                dead.append(code)
        assert dead == []


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
