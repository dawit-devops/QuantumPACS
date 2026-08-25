"""NS1 substrate tests: migration 100 DDL/grant content plus the
db/nursing.py CRUD layer (fake-conn harness mirroring test_encounters)."""
import json
from unittest.mock import MagicMock

import pytest


class _RecordingConn:
    """Captures executed SQL and returns scripted fetch results."""

    def __init__(self):
        self.queries: list[str] = []
        self._fetchrow = None
        self._fetch: list = []

    def set_fetchrow(self, value):
        self._fetchrow = value

    def set_fetch(self, value):
        self._fetch = value

    async def execute(self, sql, *args):
        self.queries.append(sql)
        return 'OK'

    async def fetchrow(self, sql, *args):
        self.queries.append(sql)
        return self._fetchrow

    async def fetch(self, sql, *args):
        self.queries.append(sql)
        return self._fetch

    async def fetchval(self, sql, *args):
        self.queries.append(sql)
        return None


def _last_sql(conn, fragment):
    hits = [q for q in conn.queries if fragment.lower() in q.lower()]
    assert hits, f'no query containing {fragment!r} in {conn.queries}'
    return hits[-1]


# ---------------------------------------------------------------------------
# Migration 100: DDL + G3 grant application
# ---------------------------------------------------------------------------

class TestMigration100NursingSurfaces:
    def _load(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            'mig100',
            'migrations/versions/100_nursing_surfaces.py',
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _with_fake_op(monkeypatch, mod, conn):
        """The alembic `op` proxy only works inside a migration context —
        swap in a recording stand-in exposing get_bind()/execute()."""

        class _FakeOp:
            def get_bind(self):
                return conn

            def execute(self, stmt):
                conn.executed.append(str(stmt))

        monkeypatch.setattr(mod, 'op', _FakeOp())

    def test_revision_chain_follows_099(self):
        mod = self._load()
        assert mod.revision == '100'
        assert mod.down_revision == '099'

    def test_upgrade_alters_vitals_and_creates_new_tables(self):
        mod = self._load()
        conn = MagicMock()
        conn.executed = []
        with pytest.MonkeyPatch.context() as mp:
            self._with_fake_op(mp, mod, conn)
            mod.upgrade()
        sql = '\n'.join(conn.executed)
        # N-01: weight/height land on the 037 vitals table.
        assert 'ADD COLUMN IF NOT EXISTS weight_kg' in sql
        assert 'ADD COLUMN IF NOT EXISTS height_cm' in sql
        # Tenant tags on the used 037 tables (pool+tag isolation convention).
        assert 'ALTER TABLE vitals ADD COLUMN IF NOT EXISTS tenant_id' in sql
        assert (
            'ALTER TABLE prep_checklists ADD COLUMN IF NOT EXISTS tenant_id'
            in sql
        )
        # N-03 / N-04 storage.
        assert 'CREATE TABLE IF NOT EXISTS contrast_consents' in sql
        assert 'signature_png' in sql
        assert 'CREATE TABLE IF NOT EXISTS exam_notes' in sql
        assert 'author_role' in sql

    def test_upgrade_appends_g3_grants_to_coordinator(self):
        """G3 (human-approved): NURSING_READ/WRITE join MATRIX_B_COORD; the
        migration ships both grants into the built-in role's jsonb."""
        mod = self._load()
        roles = [
            ('role-uuid', json.dumps(['PATIENT_READ', 'ORDER_READ'])),
            ('role-uuid-2', json.dumps(['NURSING_READ'])),  # partially granted
        ]
        captured = []

        class _FakeResult:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        conn = MagicMock()
        conn.executed = []

        def execute(query, params=None):
            captured.append((str(query), params))
            if 'SELECT id, permissions FROM roles' in str(query):
                return _FakeResult(roles)
            return _FakeResult([])

        conn.execute = MagicMock(side_effect=execute)

        class _FakeOp:
            def get_bind(self):
                return conn

            def execute(self, stmt):
                conn.executed.append(str(stmt))

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, 'op', _FakeOp())
            mod.upgrade()

        updates = [p for q, p in captured if p and 'permissions' in (p or {})]
        assert len(updates) == 2
        first = json.loads(updates[0]['permissions'])
        assert 'NURSING_READ' in first and 'NURSING_WRITE' in first
        # Idempotent append: the second role keeps its existing NURSING_READ
        # instead of duplicating it.
        second = json.loads(updates[1]['permissions'])
        assert second.count('NURSING_READ') == 1
        assert 'NURSING_WRITE' in second
        # JWTs embed permissions at login: holders must re-auth.
        bumps = [q for q, p in captured if 'token_version' in q]
        assert bumps, 'token_version bump missing'

    def test_downgrade_removes_grants(self):
        mod = self._load()

        class _FakeResult:
            def fetchall(self):
                return []

        conn = MagicMock()
        conn.executed = []
        conn.execute = MagicMock(return_value=_FakeResult())

        class _FakeOp:
            def get_bind(self):
                return conn

            def execute(self, stmt):
                conn.executed.append(str(stmt))

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, 'op', _FakeOp())
            mod.downgrade()
        sql = '\n'.join(conn.executed)
        assert 'DROP TABLE IF EXISTS exam_notes' in sql
        assert 'DROP TABLE IF EXISTS contrast_consents' in sql


# ---------------------------------------------------------------------------
# db/nursing.py CRUD layer
# ---------------------------------------------------------------------------

class TestDbVitals:
    @pytest.mark.asyncio
    async def test_record_inserts_full_vitals_row(self):
        from db.nursing import ExamVitals

        conn = _RecordingConn()
        conn.set_fetchrow({'id': 'v1', 'bp_systolic': 120})
        row = await ExamVitals(conn).record(
            exam_id='e-1', patient_id='P-1', bp_systolic=120,
            bp_diastolic=80, heart_rate=72, spo2=98, temperature_c=36.8,
            respiration=16, weight_kg=70.5, height_cm=175, by='u1',
            tenant_id='default',
        )
        assert row['id'] == 'v1'
        sql = _last_sql(conn, 'INSERT INTO vitals')
        assert 'weight_kg' in sql and 'height_cm' in sql
        assert 'tenant_id' in sql

    @pytest.mark.asyncio
    async def test_list_scopes_by_tenant_and_exam(self):
        from db.nursing import ExamVitals

        conn = _RecordingConn()
        conn.set_fetch([])
        rows = await ExamVitals(conn).list_for_exam(
            'e-1', tenant_id='default',
        )
        assert rows == []
        sql = _last_sql(conn, 'SELECT')
        assert 'FROM vitals' in sql
        assert 'ORDER BY recorded_at DESC' in sql


class TestDbPrepChecklists:
    @pytest.mark.asyncio
    async def test_get_or_create_seeds_spec_defaults(self):
        from db.nursing import DEFAULT_CHECKLIST_ITEMS, PrepChecklists

        seed_row = {
            'id': 'c1', 'exam_id': 'e-1', 'status': 'in_progress',
            'items': [],
        }
        captured_args = []
        conn = _RecordingConn()

        async def fetchrow(sql, *args):
            conn.queries.append(sql)
            if 'INSERT INTO prep_checklists' in sql:
                captured_args.append(args)
                return seed_row
            return None

        conn.fetchrow = fetchrow
        row = await PrepChecklists(conn).get_or_create(
            exam_id='e-1', patient_id='P-1', tenant_id='default',
        )
        assert row['id'] == 'c1'
        # The seeded items arrive as the $4::jsonb parameter — spec §2.11
        # N-02's five required checks must all be present and required.
        items = json.loads(captured_args[0][3])
        keys = {i['key'] for i in items}
        assert keys == {
            'allergy_verification', 'medication_review', 'npo_status',
            'consent_form', 'id_band_verified',
        }
        assert all(i['required'] is True for i in items)
        assert items == DEFAULT_CHECKLIST_ITEMS

    @pytest.mark.asyncio
    async def test_confirm_sets_complete_and_attributions(self):
        from db.nursing import PrepChecklists

        conn = _RecordingConn()
        conn.set_fetchrow({'id': 'c1'})
        await PrepChecklists(conn).confirm('c1', by='u9')
        sql = _last_sql(conn, "SET status")
        assert "'complete'" in sql.replace('"complete"', "'complete'")
        assert 'confirmed_by' in sql and 'confirmed_at' in sql


class TestDbContrastConsentsAndNotes:
    @pytest.mark.asyncio
    async def test_consent_create_stores_signature_and_version(self):
        from db.nursing import ContrastConsents

        conn = _RecordingConn()
        conn.set_fetchrow({'id': 'k1'})
        await ContrastConsents(conn).create(
            exam_id='e-1', patient_id='P-1', accepted=True,
            signature_png='data:image/png;base64,AAAA',
            consent_text_version='v1', by='u5', tenant_id='default',
        )
        sql = _last_sql(conn, 'INSERT INTO contrast_consents')
        assert 'signature_png' in sql and 'consent_text_version' in sql

    @pytest.mark.asyncio
    async def test_note_add_inserts_with_author(self):
        from db.nursing import ExamNotes

        conn = _RecordingConn()
        conn.set_fetchrow({'id': 'n1'})
        await ExamNotes(conn).add(
            exam_id='e-1', patient_id='P-1',
            note='Patient prepped and ready.', author_id='u7',
            tenant_id='default',
        )
        sql = _last_sql(conn, 'INSERT INTO exam_notes')
        assert 'author_id' in sql

    @pytest.mark.asyncio
    async def test_notes_list_orders_desc(self):
        from db.nursing import ExamNotes

        conn = _RecordingConn()
        conn.set_fetch([])
        rows = await ExamNotes(conn).list_for_exam('e-1')
        assert rows == []
        sql = _last_sql(conn, 'FROM exam_notes')
        assert 'ORDER BY created_at DESC' in sql


class TestChecklistJsonbDecoding:
    @pytest.mark.asyncio
    async def test_items_jsonb_string_is_decoded(self):
        """asyncpg returns jsonb as a raw string without a type codec — the
        db layer must hand handlers/clients a list (live-smoke regression:
        the API returned a 387-char string where the item array belonged)."""
        import json as _json

        from db.nursing import PrepChecklists

        stored = {
            'id': 'c1', 'status': 'in_progress',
            'items': _json.dumps([
                {'key': 'npo_status', 'label': 'NPO status verified',
                 'required': True, 'checked': True},
            ]),
        }

        class _Conn:
            async def fetchrow(self, sql, *args):
                return dict(stored)

        row = await PrepChecklists(_Conn()).get_or_create(
            exam_id='e-1', patient_id='P-1',
        )
        assert isinstance(row['items'], list)
        assert row['items'][0]['key'] == 'npo_status'
