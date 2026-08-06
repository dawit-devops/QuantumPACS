from unittest.mock import MagicMock, patch

import asyncio


def _setup_lifecycle_state():
    import lifecycle
    app = MagicMock()
    lifecycle.set_app(app)
    app.state.lifecycle = lifecycle.LifecycleState()
    return lifecycle


class TestDicomLifecycleFunctions:
    def test_start_dicom_creates_ae_with_correct_title(self):
        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            lifecycle._run_dicom()

            mock_ae_class.assert_called_once()
            assert mock_ae_instance.ae_title == 'QUANTUMPACS'

    def test_start_dicom_uses_configured_port(self):
        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            lifecycle._run_dicom()

            mock_ae_instance.start_server.assert_called_once()
            args, _ = mock_ae_instance.start_server.call_args
            assert args[0] == ('', 11112)

    def test_start_dicom_registers_cstore_handler(self):
        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            lifecycle._run_dicom()

            mock_ae_instance.start_server.assert_called_once()
            _, kwargs = mock_ae_instance.start_server.call_args
            assert 'evt_handlers' in kwargs

    def test_stop_dicom_shuts_down_scp(self):
        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            lifecycle._run_dicom()
            lifecycle._stop_dicom()

            mock_scp.shutdown.assert_called_once()

    def test_stop_dicom_handles_no_server(self):
        lifecycle = _setup_lifecycle_state()
        lifecycle._stop_dicom()

    def test_dcm_server_handlers_no_cmove_cget(self):
        from pynetdicom import evt
        import dcm.server
        handler_events = [h[0] for h in dcm.server.handlers]
        assert evt.EVT_C_FIND in handler_events
        # C-MOVE/C-GET are intentionally not handled (CR-02): advertising a
        # context we answer with 0x0000 while transferring nothing would
        # silently break SCUs, so the association must be refused instead.
        assert evt.EVT_C_MOVE not in handler_events
        assert evt.EVT_C_GET not in handler_events

    def test_start_dicom_sets_dcm_server_loop(self):
        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server') as mock_dcm_server:
                lifecycle._run_dicom()

                assert mock_dcm_server._loop is not None
                assert isinstance(mock_dcm_server._loop, asyncio.AbstractEventLoop)

    def test_start_dicom_includes_mwl_context(self):
        from pynetdicom.sop_class import ModalityWorklistInformationFind

        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server'):
                lifecycle._run_dicom()

                assert any(
                    pc.abstract_syntax == ModalityWorklistInformationFind
                    for pc in mock_ae_instance.supported_contexts
                )

    def test_start_dicom_includes_qr_find_contexts(self):
        from pynetdicom.sop_class import (
            PatientRootQueryRetrieveInformationModelFind,
            StudyRootQueryRetrieveInformationModelFind,
            PatientRootQueryRetrieveInformationModelMove,
            StudyRootQueryRetrieveInformationModelMove,
            PatientRootQueryRetrieveInformationModelGet,
            StudyRootQueryRetrieveInformationModelGet,
        )

        lifecycle = _setup_lifecycle_state()
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            with patch('dcm.server'):
                lifecycle._run_dicom()

                for sop_class in (
                    PatientRootQueryRetrieveInformationModelFind,
                    StudyRootQueryRetrieveInformationModelFind,
                ):
                    assert any(
                        pc.abstract_syntax == sop_class
                        for pc in mock_ae_instance.supported_contexts
                    )
                # C-MOVE/C-GET must not be advertised (CR-02).
                for sop_class in (
                    PatientRootQueryRetrieveInformationModelMove,
                    StudyRootQueryRetrieveInformationModelMove,
                    PatientRootQueryRetrieveInformationModelGet,
                    StudyRootQueryRetrieveInformationModelGet,
                ):
                    assert not any(
                        pc.abstract_syntax == sop_class
                        for pc in mock_ae_instance.supported_contexts
                    )
