"""Tests for the MPPS consumer service (S6-07) and ris_mpps_events table (S6-08).

The MPPS consumer handles DICOM Modality Performed Procedure Step messages:
- N-CREATE → marks worklist entry as IN_PROGRESS, creates/updates exam
- N-SET    → marks worklist entry as COMPLETED/DISCONTINUED, finalizes exam

RED: these tests describe the public behavior of the MppsConsumer and
RisMppsEvents model. The implementation does not exist yet.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fake_event(accession='ACC001', mpps_status='IN_PROGRESS',
                study_uid='1.2.3.4.5', station_ae='CT01'):
    """Build a mock pynetdicom N-CREATE/N-SET event."""
    from pydicom.dataset import Dataset
    ds = Dataset()
    ds.AccessionNumber = accession
    ds.StudyInstanceUID = study_uid
    ds.ScheduledProcedureStepSequence = [Dataset()]
    ds.ScheduledProcedureStepSequence[0].Modality = 'CT'
    ds.ScheduledProcedureStepSequence[0].ScheduledStationAETitle = station_ae
    ds.ScheduledProcedureStepSequence[0].ScheduledProcedureStepStatus = mpps_status

    event = MagicMock()
    event.identifier = ds
    event.assoc = MagicMock()
    event.assoc.requestor = MagicMock()
    event.assoc.requestor.ae_title = station_ae
    return event


def _fake_conn_factory(rows=None, fetchrow_result=None, fetchval_result=None):
    """Build an async connection mock that returns configured results."""
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=rows or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetchval = AsyncMock(return_value=fetchval_result)
    conn.execute = AsyncMock()
    return conn


# ---------------------------------------------------------------------------
# S6-08: ris_mpps_events table tests
# ---------------------------------------------------------------------------

class TestRisMppsEvents:
    """S6-08: The MPPS events table persists lifecycle events for audit."""

    def test_model_class_exists(self):
        from db.ris_mpps import RisMppsEvents
        assert RisMppsEvents is not None

    @pytest.mark.asyncio
    async def test_create_event_inserts_row(self):
        """An N-CREATE event is persisted with accession, status, and timestamps."""
        from db.ris_mpps import RisMppsEvents
        conn = _fake_conn_factory(fetchval_result=str(uuid.uuid4()))
        events = RisMppsEvents(conn)
        event_id = await events.create(
            accession_number='ACC001',
            event_type='N_CREATE',
            mpps_status='IN_PROGRESS',
            study_uid='1.2.3.4.5',
            raw_message='{}',
        )
        assert event_id is not None
        conn.fetchval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_by_accession_returns_events(self):
        """Events can be queried by accession number for audit trail."""
        from db.ris_mpps import RisMppsEvents
        now = datetime.now(timezone.utc)
        row = {
            'id': str(uuid.uuid4()),
            'accession_number': 'ACC001',
            'event_type': 'N_CREATE',
            'mpps_status': 'IN_PROGRESS',
            'study_uid': '1.2.3.4.5',
            'created_at': now,
        }
        conn = _fake_conn_factory(rows=[row])
        events = RisMppsEvents(conn)
        result = await events.list_by_accession('ACC001')
        assert len(result) == 1
        assert result[0]['accession_number'] == 'ACC001'


# ---------------------------------------------------------------------------
# S6-07: MPPS consumer service tests
# ---------------------------------------------------------------------------

class TestMppsConsumer:
    """S6-07: The MPPS consumer handles DICOM N-CREATE and N-SET messages."""

    def test_consumer_class_exists(self):
        from services.mpps_consumer.service import MppsConsumer
        assert MppsConsumer is not None

    def test_consumer_instantiates(self):
        from services.mpps_consumer.service import MppsConsumer
        consumer = MppsConsumer()
        assert consumer is not None

    @pytest.mark.asyncio
    async def test_n_create_sets_worklist_in_progress(self):
        """N-CREATE with accession → worklist entry status = in_progress."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC100', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-1', 'accession_number': 'ACC100',
                             'status': 'scheduled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is True
        # Should update worklist status to in_progress
        assert conn.execute.await_count >= 1

    @pytest.mark.asyncio
    async def test_n_create_records_mpps_event(self):
        """N-CREATE persists an audit event in ris_mpps_events."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC101', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-2', 'accession_number': 'ACC101',
                             'status': 'scheduled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await consumer.handle_n_create(event)

        # At least one execute call should be for the events table
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('ris_mpps_events' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_set_completed_marks_performed(self):
        """N-SET with COMPLETED → worklist entry → performed."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC200', mpps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-3', 'accession_number': 'ACC200',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('performed' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_set_discontinued_marks_cancelled(self):
        """N-SET with DISCONTINUED → worklist entry → cancelled."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC300', mpps_status='DISCONTINUED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-4', 'accession_number': 'ACC300',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('cancelled' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_create_unknown_accession_returns_false(self):
        """N-CREATE with unknown accession returns False (no worklist match)."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='UNKNOWN999', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(fetchrow_result=None)
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_n_create_no_accession_returns_false(self):
        """N-CREATE without accession number returns False."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory()
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is False


# ---------------------------------------------------------------------------
# S6-12: MPPS → exam status linkage tests
# ---------------------------------------------------------------------------

class TestMppsExamLinkage:
    """S6-12: MPPS events drive exam status transitions."""

    @pytest.mark.asyncio
    async def test_n_create_updates_exam_to_in_progress(self):
        """N-CREATE with matching exam → exam.status = in_progress."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC400', mpps_status='IN_PROGRESS',
                           study_uid='1.9.9.9.1')
        # Worklist entry exists
        wl_row = {'id': 'wl-5', 'accession_number': 'ACC400',
                  'status': 'scheduled'}
        # Exam exists with matching accession
        exam_row = {'id': 'ex-1', 'accession_number': 'ACC400',
                    'status': 'pending'}
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(side_effect=[wl_row, exam_row])
        conn.execute = AsyncMock()

        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is True
        # Verify exam status update was issued
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('exams' in c and 'in_progress' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_set_completed_updates_exam(self):
        """N-SET COMPLETED → exam.status = completed."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC500', mpps_status='COMPLETED')
        wl_row = {'id': 'wl-6', 'accession_number': 'ACC500',
                  'status': 'in_progress'}
        exam_row = {'id': 'ex-2', 'accession_number': 'ACC500',
                    'status': 'in_progress'}
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(side_effect=[wl_row, exam_row])
        conn.execute = AsyncMock()

        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('exams' in c and 'completed' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_set_no_exam_still_updates_worklist(self):
        """N-SET without matching exam still updates worklist."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC600', mpps_status='COMPLETED')
        wl_row = {'id': 'wl-7', 'accession_number': 'ACC600',
                  'status': 'in_progress'}
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        # First call returns worklist row, second returns None (no exam)
        conn.fetchrow = AsyncMock(side_effect=[wl_row, None])
        conn.execute = AsyncMock()

        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        # Worklist should still be updated
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('worklist_entries' in c for c in calls)


# ---------------------------------------------------------------------------
# S6-07: DICOM handler wiring tests
# ---------------------------------------------------------------------------

class TestMppsHandlersWired:
    """S6-07: MPPS N-CREATE/N-SET handlers are registered in dcm/server.py."""

    def test_handlers_include_n_create(self):
        from dcm.server import handlers
        from pynetdicom import evt
        event_types = [h[0] for h in handlers]
        assert evt.EVT_N_CREATE in event_types

    def test_handlers_include_n_set(self):
        from dcm.server import handlers
        from pynetdicom import evt
        event_types = [h[0] for h in handlers]
        assert evt.EVT_N_SET in event_types


class TestMppsLifecycleWiring:
    """S6-07: MPPS SCP is wired into lifecycle.py for background startup."""

    def test_mpps_scp_function_exists(self):
        from lifecycle import _run_dicom_mpps_scp
        assert callable(_run_dicom_mpps_scp)

    def test_mpps_scp_function_has_port_param(self):
        import inspect
        from lifecycle import _run_dicom_mpps_scp
        sig = inspect.signature(_run_dicom_mpps_scp)
        assert 'port' in sig.parameters

    def test_config_key_defaults_to_11114(self):
        """Default MPPS port is 11114 — must not collide with C-STORE (11112)
        or MWL (11113)."""
        from config import config
        # Verify the config key exists with expected default
        default_port = config.get('dicom_mpps_port', '11114')
        assert default_port == '11114'
        # Must not collide with other DICOM ports
        cstore = config.get('dicom_cstore_port', '11112')
        mwl = config.get('dicom_mwl_port', '11113')
        assert default_port != cstore
        assert default_port != mwl
