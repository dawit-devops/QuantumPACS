"""Tests for services/reading_handoff.py — auto handoff bridge.

Mirrors the mocking style of tests/test_dcm.py (async mock conns,
patch config/db helpers at the module level).
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest


@pytest.fixture(autouse=True)
def _reset_settle_tasks():
    from services.reading_handoff import _settle_tasks
    _settle_tasks.clear()
    yield


class TestHandoffEnabled:
    def test_default_true(self):
        from services.reading_handoff import _handoff_enabled
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            assert _handoff_enabled() is True

    def test_explicit_false(self):
        from services.reading_handoff import _handoff_enabled
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'false'}):
            assert _handoff_enabled() is False

    def test_missing_key(self):
        from services.reading_handoff import _handoff_enabled
        with patch('services.reading_handoff.config', {}):
            assert _handoff_enabled() is True


class TestSettleSeconds:
    def test_default(self):
        from services.reading_handoff import _settle_seconds
        assert _settle_seconds() == 60

    def test_custom(self):
        from services.reading_handoff import _settle_seconds
        with patch('services.reading_handoff.config', {'auto_handoff_settle_seconds': '10'}):
            assert _settle_seconds() == 10

    def test_zero(self):
        from services.reading_handoff import _settle_seconds
        with patch('services.reading_handoff.config', {'auto_handoff_settle_seconds': '0'}):
            assert _settle_seconds() == 0

    def test_invalid(self):
        from services.reading_handoff import _settle_seconds
        with patch('services.reading_handoff.config', {'auto_handoff_settle_seconds': 'abc'}):
            assert _settle_seconds() == 60


class TestEffectiveAccession:
    def test_real_accession(self):
        from services.reading_handoff import _effective_accession
        meta = {'accession_number': 'ACC001', 'study_instance_uid': '1.2.3.4'}
        assert _effective_accession(meta) == 'ACC001'

    def test_empty_accession_synthesizes(self):
        from services.reading_handoff import _effective_accession
        meta = {'accession_number': '', 'study_instance_uid': '1.2.3.4.5.6.7.8'}
        assert _effective_accession(meta) == 'AUTO-12345678'

    def test_no_study_uid_returns_empty(self):
        from services.reading_handoff import _effective_accession
        meta = {'accession_number': ''}
        assert _effective_accession(meta) == ''

    def test_whitespace_accession(self):
        from services.reading_handoff import _effective_accession
        meta = {'accession_number': '  ACC001  ', 'study_instance_uid': '1.2.3'}
        assert _effective_accession(meta) == 'ACC001'


class TestWorklistOwns:
    @pytest.mark.asyncio
    async def test_false_when_no_row(self):
        from services.reading_handoff import _worklist_owns
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        result = await _worklist_owns(conn, 'ACC001', 'default')
        assert result is False

    @pytest.mark.asyncio
    async def test_true_when_row_exists(self):
        from services.reading_handoff import _worklist_owns
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={'id': 'abc'})
        result = await _worklist_owns(conn, 'ACC001', 'default')
        assert result is True

    @pytest.mark.asyncio
    async def test_false_when_empty_accession(self):
        from services.reading_handoff import _worklist_owns
        conn = AsyncMock()
        result = await _worklist_owns(conn, '', 'default')
        assert result is False


class TestEnsureExam:
    @pytest.mark.asyncio
    async def test_creates_new_exam(self):
        from services.reading_handoff import _ensure_exam
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value='new-exam-uuid')
        meta = {
            'patient_id': 'P001',
            'patient_name': 'Test^Patient',
            'patient_birth_date': '20000101',
            'patient_sex': 'M',
            'accession_number': 'ACC001',
            'study_description': 'Chest X-Ray',
            'modality': 'CR',
            'study_instance_uid': '1.2.3.4.5',
        }
        exam_id, created = await _ensure_exam(conn, meta, 'default')
        assert exam_id == 'new-exam-uuid'
        assert created is True
        sql, *args = conn.fetchval.call_args[0]
        assert 'INSERT INTO exams' in sql
        assert 'WHERE NOT EXISTS' in sql
        assert 'ACC001' in args
        conn.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_existing(self):
        from services.reading_handoff import _ensure_exam
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value={'id': 'existing-uuid'})
        meta = {'patient_id': 'P001', 'patient_name': 'T', 'accession_number': 'ACC001',
                'study_instance_uid': '1.2.3.4.5'}
        exam_id, created = await _ensure_exam(conn, meta, 'default')
        assert exam_id == 'existing-uuid'
        assert created is False

    @pytest.mark.asyncio
    async def test_no_accession_synthesizes_and_backfills_study(self):
        from services.reading_handoff import _ensure_exam
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value='new-uuid')
        meta = {
            'patient_id': 'P001', 'patient_name': 'Test',
            'accession_number': '', 'study_description': 'Chest',
            'modality': 'CR', 'study_instance_uid': '1.2.3.4.5.6.7',
        }
        exam_id, created = await _ensure_exam(conn, meta, 'default')
        assert exam_id == 'new-uuid'
        conn.execute.assert_called_once()
        sql, *args = conn.execute.call_args[0]
        assert 'UPDATE studies' in sql
        assert 'AUTO-1234567' in args

    @pytest.mark.asyncio
    async def test_returns_none_when_missing_required_fields(self):
        from services.reading_handoff import _ensure_exam
        conn = AsyncMock()
        result = await _ensure_exam(conn, {}, 'default')
        assert result == (None, False)


class _FakeAc:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False


def _base_meta(**overrides):
    meta = {
        'patient_id': 'P001',
        'patient_name': 'Test^Patient',
        'patient_birth_date': '20000101',
        'patient_sex': 'M',
        'accession_number': 'ACC001',
        'study_description': 'Chest X-Ray',
        'modality': 'CR',
        'study_instance_uid': '1.2.3.4.5.6',
    }
    meta.update(overrides)
    return meta


class _FakeConn:
    """Deterministic asyncpg connection fake keyed on SQL shape."""

    def __init__(self, study_row=None, existing_exam=None):
        self.study_row = study_row
        self.existing_exam = existing_exam
        self.execute_calls = []
        self.exam_inserted = None
        self.transaction = MagicMock(return_value=_FakeAc())

    async def fetchrow(self, sql, *args):
        if 'worklist_entries' in sql:
            return None
        if 'FROM studies' in sql:
            return self.study_row
        if 'FROM exams' in sql:
            return self.existing_exam
        return None

    async def fetchval(self, sql, *args):
        if 'INSERT INTO exams' in sql:
            if self.existing_exam is not None:
                return None  # WHERE NOT EXISTS skipped insert
            self.exam_inserted = args
            return 'exam-uuid-1'
        return None

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))


class TestEnsureReadingExam:
    """Integration-style tests with deterministic fake conns."""

    def _study_row(self, status='receiving', received=0, updated_ago=0):
        return {
            'received_instances': received,
            'expected_instances': 0,
            'study_status': status,
            'updated_at': datetime.now(timezone.utc) - timedelta(seconds=updated_ago),
        }

    @pytest.mark.asyncio
    async def test_disabled_config_returns_none(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row())
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'false'}):
            result = await ensure_reading_exam(
                conn, _base_meta(), 'default',
            )
        assert result is None
        assert conn.exam_inserted is None

    @pytest.mark.asyncio
    async def test_missing_study_uid_returns_none(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row())
        result = await ensure_reading_exam(conn, _base_meta(study_instance_uid=''), 'default')
        assert result is None
        assert conn.exam_inserted is None

    @pytest.mark.asyncio
    async def test_missing_patient_id_returns_none(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row())
        result = await ensure_reading_exam(conn, _base_meta(patient_id=''), 'default')
        assert result is None

    @pytest.mark.asyncio
    async def test_worklist_guard_skips_when_exam_already_created(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row())
        # A real worklist entry would prevent exam creation entirely; with the
        # fake's worklist lookup pinned to None we instead assert MWL-owned
        # accessions never reach the INSERT by stubbing the worklist check.
        with patch('services.reading_handoff._worklist_owns', new=AsyncMock(return_value=True)):
            with patch('services.reading_handoff._schedule_settle'):
                result = await ensure_reading_exam(conn, _base_meta(), 'default')
        assert result is None
        assert conn.exam_inserted is None

    @pytest.mark.asyncio
    async def test_creates_exam_and_completes_when_status_complete(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row(
            status='complete', received=10,
        ))
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            with patch('services.reading_handoff._schedule_settle') as mock_sched:
                with patch('services.reading_handoff.notify_role', new=AsyncMock()):
                    with patch('services.reading_handoff.AuditLog') as mock_audit_cls:
                        mock_audit_cls.return_value.log_event = AsyncMock()
                        result = await ensure_reading_exam(conn, _base_meta(), 'default')
        assert result == 'exam-uuid-1'
        assert conn.exam_inserted is not None
        # study_status='complete' → completed immediately, no settle scheduled
        mock_sched.assert_not_called()
        assert any('UPDATE exams' in c[0] and 'completed' in c[0] for c in conn.execute_calls)

    @pytest.mark.asyncio
    async def test_creates_exam_and_schedules_settle_when_receiving(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row(status='receiving', received=0))
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            with patch('services.reading_handoff._schedule_settle') as mock_sched:
                with patch('services.reading_handoff.notify_role', new=AsyncMock()):
                    with patch('services.reading_handoff.AuditLog') as mock_audit_cls:
                        mock_audit_cls.return_value.log_event = AsyncMock()
                        result = await ensure_reading_exam(conn, _base_meta(), 'default')
        assert result == 'exam-uuid-1'
        assert conn.exam_inserted is not None
        # Not complete → settle scheduled
        mock_sched.assert_called_once()

    @pytest.mark.asyncio
    async def test_completes_via_settle_window_when_study_old(self):
        from services.reading_handoff import ensure_reading_exam
        # updated 120s ago (settle=60) → flips immediately without schedule
        conn = _FakeConn(study_row=self._study_row(
            status='receiving', received=0, updated_ago=120,
        ))
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            with patch('services.reading_handoff._schedule_settle') as mock_sched:
                with patch('services.reading_handoff.notify_role', new=AsyncMock()):
                    with patch('services.reading_handoff.AuditLog') as mock_audit_cls:
                        mock_audit_cls.return_value.log_event = AsyncMock()
                        result = await ensure_reading_exam(conn, _base_meta(), 'default')
        assert result == 'exam-uuid-1'
        mock_sched.assert_not_called()
        assert any('UPDATE exams' in c[0] and 'completed' in c[0] for c in conn.execute_calls)

    @pytest.mark.asyncio
    async def test_notify_and_audit_only_on_first_exam(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(study_row=self._study_row())
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            with patch('services.reading_handoff._schedule_settle'):
                with patch('services.reading_handoff.notify_role', new=AsyncMock()) as mock_notify:
                    with patch('services.reading_handoff.AuditLog') as mock_audit_cls:
                        mock_audit_cls.return_value.log_event = AsyncMock()
                        await ensure_reading_exam(conn, _base_meta(), 'default')
                        # Second instance of the same study: exam already exists
                        conn.existing_exam = {'id': 'exam-uuid-1'}
                        await ensure_reading_exam(conn, _base_meta(), 'default')
        mock_notify.assert_called_once()
        assert mock_audit_cls.return_value.log_event.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_existing_exam_id_without_notify(self):
        from services.reading_handoff import ensure_reading_exam
        conn = _FakeConn(
            study_row=self._study_row(),
            existing_exam={'id': 'pre-existing-uuid'},
        )
        with patch('services.reading_handoff.config', {'auto_reading_handoff': 'true'}):
            with patch('services.reading_handoff._schedule_settle'):
                with patch('services.reading_handoff.notify_role', new=AsyncMock()) as mock_notify:
                    with patch('services.reading_handoff.AuditLog') as mock_audit_cls:
                        mock_audit_cls.return_value.log_event = AsyncMock()
                        result = await ensure_reading_exam(conn, _base_meta(), 'default')
        assert result == 'pre-existing-uuid'
        assert conn.exam_inserted is None
        mock_notify.assert_not_called()


class TestMaybeComplete:
    @pytest.mark.asyncio
    async def test_no_study_row_returns_false(self):
        from services.reading_handoff import _maybe_complete
        conn = _FakeConn(study_row=None)
        result = await _maybe_complete(conn, 'exam-id', '1.2.3', 60, datetime.now(timezone.utc))
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_when_study_status_complete(self):
        from services.reading_handoff import _maybe_complete
        conn = _FakeConn(study_row={
            'received_instances': 10,
            'expected_instances': 10,
            'study_status': 'complete',
            'updated_at': datetime.now(timezone.utc),
        })
        result = await _maybe_complete(conn, 'exam-id', '1.2.3', 60, datetime.now(timezone.utc))
        assert result is True
        assert conn.execute_calls

    @pytest.mark.asyncio
    async def test_complete_when_settle_elapsed(self):
        from services.reading_handoff import _maybe_complete
        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        conn = _FakeConn(study_row={
            'received_instances': 0,
            'expected_instances': 0,
            'study_status': 'receiving',
            'updated_at': old,
        })
        result = await _maybe_complete(conn, 'exam-id', '1.2.3', 60, datetime.now(timezone.utc))
        assert result is True
        assert conn.execute_calls

    @pytest.mark.asyncio
    async def test_not_complete_when_recent(self):
        from services.reading_handoff import _maybe_complete
        recent = datetime.now(timezone.utc)
        conn = _FakeConn(study_row={
            'received_instances': 0,
            'expected_instances': 0,
            'study_status': 'receiving',
            'updated_at': recent,
        })
        result = await _maybe_complete(conn, 'exam-id', '1.2.3', 60, datetime.now(timezone.utc))
        assert result is False
        assert not conn.execute_calls