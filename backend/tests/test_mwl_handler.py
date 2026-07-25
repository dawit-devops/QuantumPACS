from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydicom.dataset import Dataset

from dcm.server import handle_find, handle_find_async, _entry_to_dataset


class TestMwlCFindHandler:
    def test_handle_find_exists(self):
        assert callable(handle_find)

    def test_handle_find_is_generator(self):
        import inspect
        assert inspect.isgeneratorfunction(handle_find)

    def test_handle_find_returns_success_status(self):
        event = MagicMock()
        event.identifier = Dataset()

        with patch('dcm.server.asyncio.run_coroutine_threadsafe') as mock_run:
            mock_future = MagicMock()
            mock_future.result.return_value = []
            mock_run.return_value = mock_future

            with patch('dcm.server._loop'):
                statuses = [s for s, _ in handle_find(event)]

        assert 0x0000 in statuses

    def test_handle_find_yields_pending_status_for_results(self):
        event = MagicMock()
        event.identifier = Dataset()
        mock_ds = Dataset()
        mock_ds.PatientID = 'P001'

        with patch('dcm.server.asyncio.run_coroutine_threadsafe') as mock_run:
            mock_future = MagicMock()
            mock_future.result.return_value = [mock_ds]
            mock_run.return_value = mock_future

            with patch('dcm.server._loop'):
                results = list(handle_find(event))

        assert len(results) == 2
        assert results[0][0] == 0xFF00
        assert results[1][0] == 0x0000


class TestEntryToDataset:
    def test_converts_basic_fields(self):
        entry = {
            'patient_id': 'P001',
            'patient_name': 'Smith^John',
            'accession_number': 'ACC001',
            'modality': 'CT',
            'station_ae_title': 'CT01',
            'requested_procedure_id': 'RP1',
            'requested_procedure_desc': 'Chest CT',
        }
        ds = _entry_to_dataset(entry)
        assert ds.PatientID == 'P001'
        assert ds.PatientName == 'Smith^John'
        assert ds.AccessionNumber == 'ACC001'
        assert ds.RequestedProcedureID == 'RP1'
        assert ds.RequestedProcedureDescription == 'Chest CT'

    def test_includes_scheduled_procedure_step_sequence(self):
        entry = {
            'patient_id': 'P001',
            'modality': 'CT',
            'station_ae_title': 'CT01',
            'scheduled_date': '20260725',
            'scheduled_time': '103000',
        }
        ds = _entry_to_dataset(entry)
        assert hasattr(ds, 'ScheduledProcedureStepSequence')
        assert len(ds.ScheduledProcedureStepSequence) == 1
        sps = ds.ScheduledProcedureStepSequence[0]
        assert sps.Modality == 'CT'
        assert sps.ScheduledStationAETitle == 'CT01'
        assert sps.ScheduledProcedureStepStartDate == '20260725'

    def test_handles_empty_entry(self):
        ds = _entry_to_dataset({})
        assert ds.PatientID == ''
        assert ds.PatientName == ''


class TestHandleFindAsync:
    @pytest.mark.asyncio
    async def test_returns_results_list(self):
        query_ds = Dataset()
        query_ds.PatientID = 'P001'

        class _FakeConn:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None

        with patch('db.conn.get_conn') as mock_get_conn:
            mock_get_conn.return_value = _FakeConn()

            with patch('db.worklist.Worklist') as mock_wl_cls:
                mock_wl = MagicMock()
                mock_wl.search = AsyncMock(
                    return_value=[{'patient_id': 'P001', 'modality': 'CT'}]
                )
                mock_wl_cls.return_value = mock_wl
                results = await handle_find_async(query_ds)
                assert len(results) == 1
                assert results[0].PatientID == 'P001'

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        query_ds = Dataset()
        with patch('db.conn.get_conn', side_effect=Exception('DB down')):
            results = await handle_find_async(query_ds)
            assert results == []


class TestHandlersList:
    def test_handlers_include_cfind(self):
        from dcm.server import handlers
        from pynetdicom import evt
        event_types = [h[0] for h in handlers]
        assert evt.EVT_C_FIND in event_types

    def test_handlers_include_cstore(self):
        from dcm.server import handlers
        from pynetdicom import evt
        event_types = [h[0] for h in handlers]
        assert evt.EVT_C_STORE in event_types
