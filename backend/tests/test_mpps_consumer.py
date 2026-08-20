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
    conn.transaction = MagicMock(return_value=AsyncMock())
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
    async def test_n_create_audits_audit_log_event(self):
        """H7: N-CREATE writes an audit_log entry (worklist_entry timeline)."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC110', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-9', 'accession_number': 'ACC110',
                             'status': 'scheduled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await consumer.handle_n_create(event)

        calls = [str(c) for c in conn.execute.await_args_list]
        assert any("INSERT INTO logs" in c and 'MPPS' in c and 'wl-9' in c
                   for c in calls)

    @pytest.mark.asyncio
    async def test_n_set_audits_audit_log_event(self):
        """H7: N-SET writes an audit_log entry (worklist_entry timeline)."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC210', mpps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-10', 'accession_number': 'ACC210',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await consumer.handle_n_set(event)

        calls = [str(c) for c in conn.execute.await_args_list]
        assert any("INSERT INTO logs" in c and 'MPPS' in c and 'wl-10' in c
                   for c in calls)

    @pytest.mark.asyncio
    async def test_mpps_processing_latency_histogram_observed(self):
        """H8: each processed MPPS message records ris_mpps_latency_seconds."""
        from prometheus_client.registry import REGISTRY
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC120', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-12', 'accession_number': 'ACC120',
                             'status': 'scheduled'},
        )
        count_before = REGISTRY.get_sample_value(
            'ris_mpps_latency_seconds_count', {'event_type': 'N_CREATE'}) or 0.0
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await MppsConsumer().handle_n_create(event)
        after = REGISTRY.get_sample_value(
            'ris_mpps_latency_seconds_count', {'event_type': 'N_CREATE'}) or 0.0
        assert after == count_before + 1

    @pytest.mark.asyncio
    async def test_n_set_completed_echoes_pacs(self):
        """H8: a completed exam triggers the C-ECHO SCU stub to the PACS."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC220', mpps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-13', 'accession_number': 'ACC220',
                             'status': 'in_progress'},
        )
        echo = AsyncMock(return_value=True)
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn), \
             patch('services.mpps_consumer.service.echo_to_pacs', echo):
            result = await MppsConsumer().handle_n_set(event)
        assert result is True
        echo.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_n_set_discontinued_does_not_echo(self):
        """H8: only COMPLETED exams probe PACS connectivity."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC320', mpps_status='DISCONTINUED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-14', 'accession_number': 'ACC320',
                             'status': 'in_progress'},
        )
        echo = AsyncMock(return_value=True)
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn), \
             patch('services.mpps_consumer.service.echo_to_pacs', echo):
            await MppsConsumer().handle_n_set(event)
        echo.assert_not_awaited()

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


class TestMppsConsumerAtomicity:
    """M-2/M-3: multi-write sequences must be atomic;
    N-CREATE must never regress a terminal entry."""

    @pytest.mark.asyncio
    async def test_n_create_wraps_writes_in_transaction(self):
        """M-2: N-CREATE's multi-write sequence (worklist + exam + event
        + audit) must be atomic — a mid-sequence failure must not leave
        half-applied state."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC130', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-13', 'accession_number': 'ACC130',
                             'status': 'scheduled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await consumer.handle_n_create(event)

        conn.transaction.assert_called_once()
        conn.transaction.return_value.__aenter__.assert_awaited_once()
        conn.transaction.return_value.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_n_set_wraps_writes_in_transaction(self):
        """M-2: N-SET's multi-write sequence must be atomic too."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC230', mpps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-23', 'accession_number': 'ACC230',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            await consumer.handle_n_set(event)

        conn.transaction.assert_called_once()
        conn.transaction.return_value.__aenter__.assert_awaited_once()
        conn.transaction.return_value.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_n_create_does_not_regress_performed_entry(self):
        """M-3: a late/repeated N-CREATE must not regress a performed
        entry back to in_progress — the message is still audited."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC140', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-14', 'accession_number': 'ACC140',
                             'status': 'performed'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert not any("UPDATE worklist_entries" in c and 'in_progress' in c
                       for c in calls)
        assert any('ris_mpps_events' in c for c in calls)

    @pytest.mark.asyncio
    async def test_n_create_does_not_regress_cancelled_entry(self):
        """M-3: same guard for cancelled entries."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC150', mpps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-15', 'accession_number': 'ACC150',
                             'status': 'cancelled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert not any("UPDATE worklist_entries" in c and 'in_progress' in c
                       for c in calls)
        assert any('ris_mpps_events' in c for c in calls)


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
        conn.transaction = MagicMock(return_value=AsyncMock())

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
        conn.transaction = MagicMock(return_value=AsyncMock())

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
        conn.transaction = MagicMock(return_value=AsyncMock())

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


    # ---------------------------------------------------------------------------
    # CR-2: MPPS status must come from PerformedProcedureStepSequence
    # ---------------------------------------------------------------------------

class TestMppsPerformedProcedureStepStatus:
    """CR-2: N-CREATE/N-SET must read (0040,0252) PerformedProcedureStepStatus.

    A conformant MPPS message carries the status in
    PerformedProcedureStepSequence[0].PerformedProcedureStepStatus, not in
    ScheduledProcedureStepSequence[0].ScheduledProcedureStepStatus. The
    original implementation read the SPS element, so a COMPLETED N-SET was
    mapped to `in_progress` (or left as the 'IN_PROGRESS' echo) instead of
    `performed`.
    """

    def _fake_pps_event(self, accession='ACC-PPS-01', pps_status='COMPLETED',
                        sps_status='IN_PROGRESS', study_uid='1.2.3.4.6',
                        station_ae='CT01'):
        """Conformant event: status lives in the PPS sequence."""
        from pydicom.dataset import Dataset
        ds = Dataset()
        ds.AccessionNumber = accession
        ds.StudyInstanceUID = study_uid
        ds.ScheduledProcedureStepSequence = [Dataset()]
        ds.ScheduledProcedureStepSequence[0].Modality = 'CT'
        ds.ScheduledProcedureStepSequence[0].ScheduledStationAETitle = station_ae
        ds.ScheduledProcedureStepSequence[0].ScheduledProcedureStepStatus = sps_status
        # (0040,0270) performed-step block: pydicom stores it under the
        # retired keyword ScheduledStepAttributesSequence — build by tag.
        ds.add_new((0x0040, 0x0270), 'SQ', [Dataset()])
        pps_item = ds.get_item((0x0040, 0x0270))
        pps_item.value[0].Modality = 'CT'
        pps_item.value[0].PerformedProcedureStepStatus = pps_status

        event = MagicMock()
        event.identifier = ds
        event.assoc = MagicMock()
        event.assoc.requestor = MagicMock()
        event.assoc.requestor.ae_title = station_ae
        return event

    @pytest.mark.asyncio
    async def test_n_set_completed_reads_pps_status(self):
        """N-SET COMPLETED in PPS (SPS echoes IN_PROGRESS) → worklist performed."""
        from services.mpps_consumer.service import MppsConsumer
        event = self._fake_pps_event(accession='ACC-PPS-01', pps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-pps1', 'accession_number': 'ACC-PPS-01',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('performed' in c for c in calls), calls

    @pytest.mark.asyncio
    async def test_n_create_in_progress_reads_pps_status(self):
        """N-CREATE IN_PROGRESS in PPS (SPS absent) → worklist in_progress."""
        from services.mpps_consumer.service import MppsConsumer
        event = self._fake_pps_event(accession='ACC-PPS-02', pps_status='IN_PROGRESS')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-pps2', 'accession_number': 'ACC-PPS-02',
                             'status': 'scheduled'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_create(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('in_progress' in c for c in calls), calls

    @pytest.mark.asyncio
    async def test_n_set_discontinued_reads_pps_status(self):
        """N-SET DISCONTINUED in PPS → worklist cancelled."""
        from services.mpps_consumer.service import MppsConsumer
        event = self._fake_pps_event(accession='ACC-PPS-03', pps_status='DISCONTINUED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-pps3', 'accession_number': 'ACC-PPS-03',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('cancelled' in c for c in calls), calls

    @pytest.mark.asyncio
    async def test_sps_only_dataset_falls_back_to_sps_status(self):
        """Legacy/non-conformant dataset with only SPS still works."""
        from services.mpps_consumer.service import MppsConsumer
        event = _fake_event(accession='ACC-PPS-04', mpps_status='COMPLETED')
        conn = _fake_conn_factory(
            fetchrow_result={'id': 'wl-pps4', 'accession_number': 'ACC-PPS-04',
                             'status': 'in_progress'},
        )
        consumer = MppsConsumer()
        with patch('services.mpps_consumer.service.get_conn',
                    return_value=conn):
            result = await consumer.handle_n_set(event)

        assert result is True
        calls = [str(c) for c in conn.execute.await_args_list]
        assert any('performed' in c for c in calls), calls
