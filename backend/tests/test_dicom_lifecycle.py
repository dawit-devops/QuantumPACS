from unittest.mock import MagicMock, patch

import asyncio


class TestDicomLifecycleFunctions:
    def test_start_dicom_creates_ae_with_correct_title(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _run_dicom
            _run_dicom()

            mock_ae_class.assert_called_once()
            assert mock_ae_instance.ae_title == 'QUANTUMPACS'

    def test_start_dicom_uses_configured_port(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _run_dicom
            _run_dicom()

            mock_ae_instance.start_server.assert_called_once()
            args, _ = mock_ae_instance.start_server.call_args
            assert args[0] == ('', 11112)

    def test_start_dicom_registers_cstore_handler(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _run_dicom
            _run_dicom()

            mock_ae_instance.start_server.assert_called_once()
            _, kwargs = mock_ae_instance.start_server.call_args
            assert 'evt_handlers' in kwargs

    def test_stop_dicom_shuts_down_scp(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _run_dicom, _stop_dicom
            _run_dicom()
            _stop_dicom()

            mock_scp.shutdown.assert_called_once()

    def test_stop_dicom_handles_no_server(self):
        from lifecycle import _stop_dicom
        _stop_dicom()

    def test_dcm_server_handlers_include_cmove_cget(self):
        from pynetdicom import evt
        import dcm.server
        handler_events = [h[0] for h in dcm.server.handlers]
        assert evt.EVT_C_MOVE in handler_events
        assert evt.EVT_C_GET in handler_events

    def test_start_dicom_sets_dcm_server_loop(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server') as mock_dcm_server:
                from lifecycle import _run_dicom
                _run_dicom()

                assert mock_dcm_server._loop is not None
                assert isinstance(mock_dcm_server._loop, asyncio.AbstractEventLoop)

    def test_start_dicom_includes_mwl_context(self):
        from pynetdicom.sop_class import ModalityWorklistInformationFind

        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server'):
                from lifecycle import _run_dicom
                _run_dicom()

                assert ModalityWorklistInformationFind in mock_ae_instance.supported_contexts

    def test_start_dicom_includes_move_get_contexts(self):
        from pynetdicom.sop_class import (
            PatientRootQueryRetrieveInformationModelMove,
            StudyRootQueryRetrieveInformationModelMove,
            PatientRootQueryRetrieveInformationModelGet,
            StudyRootQueryRetrieveInformationModelGet,
        )

        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server'):
                from lifecycle import _run_dicom
                _run_dicom()

                assert PatientRootQueryRetrieveInformationModelMove in mock_ae_instance.supported_contexts
                assert StudyRootQueryRetrieveInformationModelMove in mock_ae_instance.supported_contexts
                assert PatientRootQueryRetrieveInformationModelGet in mock_ae_instance.supported_contexts
                assert StudyRootQueryRetrieveInformationModelGet in mock_ae_instance.supported_contexts
