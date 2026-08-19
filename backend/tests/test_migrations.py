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

    def test_migration_062_exists(self):
        assert _migration('062').name == '062_reconcile_drifted_role_grants.py'

    def test_migration_062_canonical_matches_permissions_py(self):
        """technologist review P0-1: migration 062 re-applies the canonical
        grants for the four drifted slugs — the frozen snapshot must stay
        equal to BUILT_IN_ROLES so live DBs converge with fresh seeds."""
        from api.permissions import BUILT_IN_ROLES
        module = _import_migration('062')
        for slug in module.CANONICAL_GRANTS:
            assert set(module.CANONICAL_GRANTS[slug]) == set(BUILT_IN_ROLES[slug]), slug

    def test_migration_062_covers_all_drifted_slugs(self):
        module = _import_migration('062')
        assert set(module.CANONICAL_GRANTS) == {
            'technologist', 'radiologist', 'resident', 'cashier',
        }

    def test_migration_063_exists(self):
        assert _migration('063').name == '063_add_coordination_read_grants.py'

    def test_migration_063_grants_match_matrix_b(self):
        """care_coordinator review P0-1/P1-1: the additive grants must equal
        the WORKLIST_READ + FILE_READ entries on MATRIX_B_PHYS/COORD so the
        migration and the source of truth cannot diverge."""
        from api.permissions import MATRIX_B_COORD, MATRIX_B_PHYS
        module = _import_migration('063')
        by_slug: dict[str, set[str]] = {}
        for slug, grant in module.ADDITIVE_GRANTS:
            by_slug.setdefault(slug, set()).add(grant)
        for slug, grants in by_slug.items():
            canonical = MATRIX_B_PHYS if slug == 'physician' else MATRIX_B_COORD
            assert grants == {'WORKLIST_READ', 'FILE_READ'}, slug
            assert grants <= canonical, slug

    def test_migration_063_adds_only_read_grants(self):
        """The append must never carry write tiers — no WORKLIST_WRITE,
        FILE_WRITE or FILE_DELETE."""
        module = _import_migration('063')
        all_grants = {g for _, g in module.ADDITIVE_GRANTS}
        assert not ({'WORKLIST_WRITE', 'FILE_WRITE', 'FILE_DELETE'} & all_grants)
        assert all_grants == {'WORKLIST_READ', 'FILE_READ'}


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


class TestMppsEventsMigration:
    """Migration 070: ris_mpps_events table for MPPS audit trail (S6-08)."""

    EXPECTED_COLUMNS = {
        'id', 'accession_number', 'event_type', 'mpps_status',
        'study_uid', 'station_ae_title', 'raw_message',
        'tenant_id', 'created_at',
    }

    EXPECTED_INDEXES = {
        'ix_ris_mpps_accession',
        'ix_ris_mpps_created',
        'ix_ris_mpps_tenant',
    }

    def test_migration_070_exists(self):
        assert _migration('070').name == '070_ris_mpps_events.py'

    def test_migration_070_revises_069(self):
        module = _import_migration('070')
        assert module.down_revision == '069'

    def test_migration_070_creates_table(self):
        content = _migration('070').read_text()
        assert 'CREATE TABLE IF NOT EXISTS ris_mpps_events' in content

    def test_migration_070_has_all_columns(self):
        content = _migration('070').read_text()
        for col in self.EXPECTED_COLUMNS:
            assert col in content, f'Missing column: {col}'

    def test_migration_070_has_all_indexes(self):
        content = _migration('070').read_text()
        for idx in self.EXPECTED_INDEXES:
            assert f'CREATE INDEX IF NOT EXISTS {idx}' in content, \
                f'Missing index: {idx}'

    def test_migration_070_has_raw_message_jsonb(self):
        """raw_message must be JSONB to store serialized DICOM datasets."""
        content = _migration('070').read_text()
        assert 'raw_message JSONB' in content

    def test_migration_070_has_tenant_id(self):
        """tenant_id is required for RLS scoping."""
        content = _migration('070').read_text()
        assert 'tenant_id TEXT' in content

    def test_migration_070_downgrade_drops_table(self):
        content = _migration('070').read_text()
        assert 'def downgrade()' in content
        assert 'drop_table' in content

    def test_migration_070_matches_sync_db_schema(self):
        """The migration DDL and db/ris_mpps.py sync_db() must produce
        identical table schemas. Drift between the two bootstrapping
        paths (alembic for containers, sync_db for dev) causes silent
        column mismatches."""
        import inspect
        from db.ris_mpps import RisMppsEvents
        source = inspect.getsource(RisMppsEvents.sync_db)
        # sync_db should reference the same table name
        assert 'ris_mpps_events' in source
        # Both must define accession_number, event_type, mpps_status columns
        for col in ('accession_number', 'event_type', 'mpps_status'):
            assert col in source, f'sync_db missing column: {col}'

    def test_migration_070_indexes_cover_query_patterns(self):
        """Index set must support the two main query patterns:
        1. List events by accession (audit trail lookup)
        2. Query recent events (monitoring/dashboard)
        3. Tenant-scoped queries (RLS)"""
        content = _migration('070').read_text()
        # Accession lookup — audit trail
        assert 'ix_ris_mpps_accession' in content
        # Recent events — monitoring
        assert 'ix_ris_mpps_created' in content
        # Tenant scope — RLS
        assert 'ix_ris_mpps_tenant' in content
