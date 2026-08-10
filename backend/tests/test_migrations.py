from pathlib import Path

from api.permissions import (
    MATRIX_A_BILL,
    MATRIX_A_RECEPT,
)



def _migration(revision):
    migrations_dir = Path(__file__).parents[1] / 'migrations' / 'versions'
    matches = sorted(migrations_dir.glob(f'{revision}_*.py'))
    if not matches:
        raise FileNotFoundError(f"Migration {revision} not found")
    return matches[0]


def _import_migration(revision):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f'migration_{revision}', _migration(revision))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestNotifyEventMigration:
    def test_migration_025_exists(self):
        assert _migration('025').name == '025_fix_notify_event.py'

    def test_migration_025_uses_coalesce_for_old(self):
        content = _migration('025').read_text()
        assert "COALESCE(row_to_json(OLD), '{}'::json)" in content

    def test_migration_025_uses_coalesce_for_new(self):
        content = _migration('025').read_text()
        assert "COALESCE(row_to_json(NEW), '{}'::json)" in content

    def test_migration_025_downgrade_restores_original(self):
        content = _migration('025').read_text()
        assert "def downgrade()" in content
        assert "row_to_json(OLD)" in content
        assert "row_to_json(NEW)" in content


class TestFrontDeskRoleGrantsMigration:
    """Migration 046: R08 grants on scheduler + receptionist (seed parity)."""

    R08 = {'REGISTRATION_READ', 'REGISTRATION_WRITE', 'QUEUE_READ'}

    def test_migration_046_exists(self):
        assert _migration('046').name == '046_front_desk_role_grants.py'

    def test_migration_046_upgrade_grants_match_permissions_py(self):
        # Drift guard: if permissions.py changes after 046 is applied, fresh
        # DBs (runtime seed_built_in_roles upsert) and upgraded DBs diverge.
        # Scheduler is dropped entirely by migration 052, so only the kept
        # receptionist row is guarded here.
        module = _import_migration('046')
        assert set(module.UPGRADE_GRANTS['receptionist']) == MATRIX_A_RECEPT

    def test_migration_046_adds_only_the_r08_grants(self):
        module = _import_migration('046')
        # Scheduler gains the three front-desk codes; receptionist also gains
        # SCHEDULE_WRITE (the R08 booking grant added to MATRIX_A_RECEPT).
        added_sched = (
            set(module.UPGRADE_GRANTS['scheduler'])
            - set(module.ROLLBACK_GRANTS['scheduler'])
        )
        assert added_sched == self.R08
        added_rec = (
            set(module.UPGRADE_GRANTS['receptionist'])
            - set(module.ROLLBACK_GRANTS['receptionist'])
        )
        assert added_rec == self.R08 | {'SCHEDULE_WRITE'}

    def test_migration_046_downgrade_restores_prior_grants(self):
        module = _import_migration('046')
        assert "def downgrade()" in _migration('046').read_text()
        # Receptionist additionally gained SCHEDULE_WRITE in MATRIX_A_RECEPT
        # (R08 booking); the migration's rollback rows are exactly what the
        # upgraded sets would be minus every grant they added.
        rollback = module.ROLLBACK_GRANTS['receptionist']
        added = set(module.UPGRADE_GRANTS['receptionist']) - set(rollback)
        assert set(rollback) == MATRIX_A_RECEPT - added


class TestLegacyRoleGrantTrimsMigration:
    """Migration 048: R2-14 legacy over-grant trims (tenant_admin, cashier,
    technologist) — upgraded DBs must match freshly-seeded ones."""

    # Legacy codes every trimmed role lost (R2-14: no clinical writes unless
    # the canonical matrix says so): the three clinical-write codes removed
    # from tenant_admin/technologist, plus the cashier gifts (it now mirrors
    # the canonical biller exactly).
    REMOVED = {'PATIENT_WRITE', 'STUDY_WRITE', 'FILE_DELETE',
               'STUDY_READ', 'FILE_READ'}

    def test_migration_048_exists(self):
        assert _migration('048').name == '048_trim_legacy_role_grants.py'

    def test_migration_048_upgrade_matches_permissions_py(self):
        from api.permissions import BUILT_IN_ROLES
        module = _import_migration('048')
        for slug in module.UPGRADE_GRANTS:
            assert set(module.UPGRADE_GRANTS[slug]) == set(BUILT_IN_ROLES[slug])

    def test_migration_048_removes_only_clinical_overgrants(self):
        module = _import_migration('048')
        tenant_admin = set(module.UPGRADE_GRANTS['tenant_admin'])
        # Matrix C grants no clinical writes — the trimmed set stays clean.
        assert not ({'PATIENT_WRITE', 'STUDY_WRITE', 'FILE_DELETE'} & tenant_admin)
        # The compliance-critical codes are gone, everything else is retained.
        assert {'PATIENT_READ', 'STUDY_READ', 'FILE_READ', 'FILE_WRITE',
                'REPLICA_READ', 'LOG_READ'} <= tenant_admin

    def test_migration_048_cashier_equals_biller(self):
        module = _import_migration('048')
        assert set(module.UPGRADE_GRANTS['cashier']) == MATRIX_A_BILL

    def test_migration_048_downgrade_restores_prior_grants(self):
        module = _import_migration('048')
        assert "def downgrade()" in _migration('048').read_text()
        for slug, rollback in module.ROLLBACK_GRANTS.items():
            removed = set(rollback) - set(module.UPGRADE_GRANTS[slug])
            assert removed <= self.REMOVED


class TestCrossTenantGrantsMigration:
    """Migration 049: R2-03 user_tenant_grants table + CROSS_TENANT_READ on
    the two clinical roles (radiologist == teleradiologist, spec §5)."""

    def test_migration_049_exists(self):
        assert _migration('049').name == '049_cross_tenant_grants.py'

    def test_migration_049_creates_grant_table(self):
        content = _migration('049').read_text()
        assert 'CREATE TABLE IF NOT EXISTS user_tenant_grants' in content
        assert 'REFERENCES users(id) ON DELETE CASCADE' in content

    def test_migration_049_adds_only_cross_tenant_read(self):
        module = _import_migration('049')
        assert module.CROSS_TENANT_READ == 'CROSS_TENANT_READ'
        assert tuple(module.AFFECTED_ROLES) == ('radiologist', 'teleradiologist')
        # The UPDATE only ever appends the one code — it must not reference
        # any other permission (048-style full-list rewrites are not needed).
        content = _migration('049').read_text()
        other_codes = [
            code for code in ('PATIENT_WRITE', 'STUDY_WRITE', 'FILE_DELETE',
                              'QUEUE_READ', 'SCHEDULE_WRITE')
            if f'"{code}"' in content
        ]
        assert other_codes == []

    def test_migration_049_matches_permissions_py(self):
        # Drift guard: runtime seed upserts BUILT_IN_ROLES on boot — the two
        # clinical roles there must carry the code the migration adds.
        from api.permissions import BUILT_IN_ROLES
        assert 'CROSS_TENANT_READ' in BUILT_IN_ROLES['radiologist']
        assert 'CROSS_TENANT_READ' in BUILT_IN_ROLES['teleradiologist']
        # RAD == TEL contracts survive the addition.
        assert set(BUILT_IN_ROLES['radiologist']) == set(BUILT_IN_ROLES['teleradiologist'])

    def test_migration_049_downgrade_removes_table_and_code(self):
        content = _migration('049').read_text()
        assert 'DROP TABLE IF EXISTS user_tenant_grants' in content
        assert "permissions - '{CROSS_TENANT_READ}'" in content
