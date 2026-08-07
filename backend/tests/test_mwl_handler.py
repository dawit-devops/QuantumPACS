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

        def _discard_coroutine(coro, loop):
            # The real scheduler would await `coro` on the DICOM thread loop;
            # here we close it so it is not left un-awaited (RuntimeWarning).
            coro.close()
            return mock_future

        with patch('dcm.server.asyncio.run_coroutine_threadsafe', side_effect=_discard_coroutine) as mock_run:
            mock_future = MagicMock()
            mock_future.result.return_value = []

            with patch('dcm.server._loop'):
                statuses = [s for s, _ in handle_find(event)]

        assert 0x0000 in statuses

    def test_handle_find_yields_pending_status_for_results(self):
        event = MagicMock()
        event.identifier = Dataset()
        mock_ds = Dataset()
        mock_ds.PatientID = 'P001'

        def _discard_coroutine(coro, loop):
            # See test_handle_find_returns_success_status — close the un-run
            # coroutine instead of leaking it un-awaited.
            coro.close()
            return mock_future

        with patch('dcm.server.asyncio.run_coroutine_threadsafe', side_effect=_discard_coroutine) as mock_run:
            mock_future = MagicMock()
            mock_future.result.return_value = [mock_ds]

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

    def test_includes_extended_mwl_fields(self):
        entry = {
            'patient_id': 'P001',
            'patient_name': 'Smith^John',
            'accession_number': 'ACC001',
            'modality': 'CT',
            'station_ae_title': 'CT01',
            'scheduled_date': '20260725',
            'scheduled_time': '103000',
            'referring_physician': 'Jones^Mary',
            'requesting_physician': 'Jones^Mary',
            'requested_procedure_priority': 'A',
            'reason_for_requested_procedure': 'Routine screening',
            'requested_procedure_code': 'CHESTCT',
            'requested_procedure_code_meaning': 'Chest CT',
            'requested_procedure_code_scheme': 'L',
            'scheduled_station_name': 'CT Room 1',
            'scheduled_performing_physician': 'Lee^Kim',
            'protocol_name': 'CHEST ROUTINE',
            'status': 'in_progress',
        }
        ds = _entry_to_dataset(entry)
        assert ds.ReferringPhysicianName == 'Jones^Mary'
        assert ds.RequestingPhysician == 'Jones^Mary'
        assert ds.RequestedProcedurePriority == 'A'
        assert len(ds.RequestedProcedureCodeSequence) == 1
        code = ds.RequestedProcedureCodeSequence[0]
        assert code.CodeValue == 'CHESTCT'
        assert code.CodeMeaning == 'Chest CT'
        assert code.CodingSchemeDesignator == 'L'
        sps = ds.ScheduledProcedureStepSequence[0]
        assert sps.ReasonForTheRequestedProcedure == 'Routine screening'
        assert sps.ScheduledStationName == 'CT Room 1'
        assert sps.ScheduledPerformingPhysicianName == 'Lee^Kim'
        assert sps.ProtocolName == 'CHEST ROUTINE'
        assert sps.ScheduledProcedureStepStatus == 'STARTED'

    def test_maps_status_to_sps_status(self):
        for status, expected in (
            ('scheduled', 'SCHEDULED'),
            ('in_progress', 'STARTED'),
            ('performed', 'COMPLETED'),
            ('cancelled', 'CANCELLED'),
            ('', 'SCHEDULED'),
        ):
            ds = _entry_to_dataset({'status': status})
            assert ds.ScheduledProcedureStepSequence[0].ScheduledProcedureStepStatus == expected

    def test_omits_code_sequence_when_no_code(self):
        ds = _entry_to_dataset({'patient_id': 'P001'})
        assert not hasattr(ds, 'RequestedProcedureCodeSequence')

    def test_formats_date_time_objects_as_dicom(self):
        # asyncpg returns DATE/TIME columns as date/time objects; str()
        # would emit '2026-07-25'/'10:30:00' which is not valid DICOM.
        from datetime import date, time
        ds = _entry_to_dataset({
            'patient_id': 'P001',
            'scheduled_date': date(2026, 7, 25),
            'scheduled_time': time(10, 30, 0),
        })
        sps = ds.ScheduledProcedureStepSequence[0]
        assert sps.ScheduledProcedureStepStartDate == '20260725'
        assert sps.ScheduledProcedureStepStartTime == '103000'

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

    @pytest.mark.filterwarnings('ignore:Invalid value for VR UI:UserWarning')
    def test_accepts_uuid_id(self):
        # asyncpg returns the id column as a uuid.UUID object; pydicom's UID
        # rejects non-str values, so _entry_to_dataset must stringify it.
        # pydicom still warns that a UUID is not a valid DICOM UI — expected,
        # the point of the test is that we tolerate such ids in the wild.
        import uuid
        uid = uuid.uuid4()
        ds = _entry_to_dataset({'id': uid})
        assert ds.file_meta.MediaStorageSOPInstanceUID == str(uid)


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
                # search() returns (rows, total) — a bare list here masked a
                # tuple-unpacking regression in handle_find_async (CR-01).
                mock_wl.search = AsyncMock(
                    return_value=([{'patient_id': 'P001', 'modality': 'CT'}], 1)
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

    @pytest.mark.asyncio
    async def test_passes_raw_patient_and_station_filters(self):
        # Raw values: Worklist.search() performs the wildcard translation,
        # so the handler must not pre-translate (would double-escape '%').
        query_ds = Dataset()
        query_ds.PatientID = 'P00*'
        query_ds.PatientName = 'Smith^J?'
        query_ds.Modality = 'CT'
        query_ds.AccessionNumber = 'ACC001'
        sps = Dataset()
        sps.ScheduledStationAETitle = 'CT01'
        query_ds.ScheduledProcedureStepSequence = [sps]

        with patch('db.conn.get_conn'):
            with patch('db.worklist.Worklist') as mock_wl_cls:
                mock_wl = MagicMock()
                mock_wl.search = AsyncMock(return_value=([], 0))
                mock_wl_cls.return_value = mock_wl
                await handle_find_async(query_ds)

        kwargs = mock_wl.search.call_args.kwargs
        assert kwargs['status'] == 'scheduled'
        assert kwargs['patient_id'] == 'P00*'
        assert kwargs['patient_name'] == 'Smith^J?'
        assert kwargs['modality'] == 'CT'
        assert kwargs['station_ae_title'] == 'CT01'
        assert kwargs['search'] == 'ACC001'

    @pytest.mark.asyncio
    async def test_splits_date_range_and_time_range(self):
        query_ds = Dataset()
        sps = Dataset()
        sps.ScheduledProcedureStepStartDate = '20260701-20260731'
        sps.ScheduledProcedureStepStartTime = '0800-1200'
        query_ds.ScheduledProcedureStepSequence = [sps]

        with patch('db.conn.get_conn'):
            with patch('db.worklist.Worklist') as mock_wl_cls:
                mock_wl = MagicMock()
                mock_wl.search = AsyncMock(return_value=([], 0))
                mock_wl_cls.return_value = mock_wl
                await handle_find_async(query_ds)

        kwargs = mock_wl.search.call_args.kwargs
        assert kwargs['date_from'] == '20260701'
        assert kwargs['date_to'] == '20260731'
        assert kwargs['time_from'] == '0800'
        assert kwargs['time_to'] == '1200'

    @pytest.mark.asyncio
    async def test_passes_requested_procedure_id(self):
        query_ds = Dataset()
        query_ds.RequestedProcedureID = 'RP-1'

        with patch('db.conn.get_conn'):
            with patch('db.worklist.Worklist') as mock_wl_cls:
                mock_wl = MagicMock()
                mock_wl.search = AsyncMock(return_value=([], 0))
                mock_wl_cls.return_value = mock_wl
                await handle_find_async(query_ds)

        kwargs = mock_wl.search.call_args.kwargs
        assert kwargs['requested_procedure_id'] == 'RP-1'


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
