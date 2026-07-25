from unittest.mock import MagicMock, patch

import pytest


class TestDicomLifecycleFunctions:
    def test_start_dicom_creates_ae_with_correct_title(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _start_dicom
            _start_dicom()

            mock_ae_class.assert_called_once()
            assert mock_ae_instance.ae_title == 'QUANTUMPACS'

    def test_start_dicom_uses_configured_port(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _start_dicom
            _start_dicom()

            mock_ae_instance.start_server.assert_called_once()
            args, _ = mock_ae_instance.start_server.call_args
            assert args[0] == ('', 11112)

    def test_start_dicom_registers_cstore_handler(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _start_dicom
            _start_dicom()

            mock_ae_instance.start_server.assert_called_once()
            _, kwargs = mock_ae_instance.start_server.call_args
            assert 'evt_handlers' in kwargs

    def test_stop_dicom_shuts_down_scp(self):
        with patch('pynetdicom.AE') as mock_ae_class:
            mock_ae_instance = MagicMock()
            mock_ae_class.return_value = mock_ae_instance
            mock_scp = MagicMock()
            mock_ae_instance.start_server.return_value = mock_scp

            from lifecycle import _start_dicom, _stop_dicom
            _start_dicom()
            _stop_dicom()

            mock_scp.shutdown.assert_called_once()

    def test_stop_dicom_handles_no_server(self):
        from lifecycle import _stop_dicom
        _stop_dicom()
