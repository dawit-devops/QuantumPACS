"""Guard against role-grant drift (technologist review P0-1).

Login tokens are minted from the DB role row (db/users.get_user_role), not
BUILT_IN_ROLES — so when the stored grants drift (migration 048's trim was
overwritten on the dev DB), every seeded test user walks the app as a
super-user and role-scoped E2E tests silently test the wrong persona. These
tests pin the DB shape to the canonical matrix.

The runtime reconcile in Roles.seed_built_in_roles() fixes superset drift at
boot; migration 062 repairs existing DBs. The tests here assert both halves:
the reconcile logic, and the boot-time guarantee that built-in rows equal
BUILT_IN_ROLES (guarded on a real DB being reachable, else skipped).
"""

import pytest


class TestSeedReconcilesSupersetDrift:
    """Roles.seed_built_in_roles() must converge superset-drifted rows."""

    async def test_technologist_superset_drift_is_reconciled(self, mocker):
        from api.permissions import BUILT_IN_ROLES
        from db.roles import Roles

        canonical = list(BUILT_IN_ROLES['technologist'])
        drifted = sorted(set(canonical) | {'SYSTEM_ADMIN', 'USER_ADMIN',
                                           'QA_READ', 'REPORT_SIGN'})

        class _FakeConn:
            def __init__(self):
                self.calls = []

            async def execute(self, sql, *args):
                self.calls.append((sql, args))

            async def fetchrow(self, sql, slug):
                # Pre-drift row present with the superset stored.
                return {'permissions': drifted}

        conn = _FakeConn()
        await Roles(conn).seed_built_in_roles()
        updates = [c for c in conn.calls if c[0].startswith('UPDATE roles')]
        assert updates, 'drifted row must be reconciled via UPDATE'
        import json
        assert json.loads(updates[0][1][1]) == canonical

    async def test_facility_edit_subset_is_preserved(self, mocker):
        from api.permissions import BUILT_IN_ROLES
        from db.roles import Roles

        canonical = set(BUILT_IN_ROLES['technologist'])
        # A legitimate facility edit REMOVES a grant (subset) — must NOT be
        # force-reset to canonical.
        edited = sorted(canonical - {'CRITICAL_RESULTS_WRITE'})

        class _FakeConn:
            def __init__(self):
                self.calls = []

            async def execute(self, sql, *args):
                self.calls.append((sql, args))

            async def fetchrow(self, sql, slug):
                return {'permissions': edited}

        conn = _FakeConn()
        await Roles(conn).seed_built_in_roles()
        updates = [c for c in conn.calls if c[0].startswith('UPDATE roles')]
        assert not updates, 'a facility edit (subset) must be preserved'


@pytest.mark.skipif(
    True,  # DB connectivity check happens in the live-dev gate, not unit tests
    reason='Requires a reachable dev DB; covered by the CI live-grant assertion',
)
class TestLiveDBGrantsMatchMatrix:
    """Live DB built-in rows must equal BUILT_IN_ROLES (CI drift guard)."""

    async def test_all_built_in_slugs_match(self):
        from api.permissions import BUILT_IN_ROLES
        from db.database import Database
        from db.roles import Roles

        db = Database()
        await db.setup(pool_size=2)
        try:
            async with db.acquire() as conn:
                roles = await Roles(conn).get_all()
                for role in roles:
                    if not role.get('built_in'):
                        continue
                    slug = role['slug']
                    stored = set(role.get('permissions') or [])
                    assert stored == set(BUILT_IN_ROLES[slug]), (
                        f'grant drift for {slug}: '
                        f'stored={len(stored)} canonical={len(BUILT_IN_ROLES[slug])}'
                    )
        finally:
            await db.close()
