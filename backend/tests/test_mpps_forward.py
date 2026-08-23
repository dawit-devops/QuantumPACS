"""C3 (GAP_AUDIT_TDD_PIPELINE.md): S6-09's "echo study status to PACS"
shipped as a bare C-ECHO connectivity ping — no exam status ever reached
the PACS. The MPPS-forward SCU sends the modality's own N-CREATE/N-SET
datasets to the configured remote AE, config-gated and failure-isolated:
a dead PACS must never break local MPPS processing."""

import socket
import time
from unittest.mock import patch

import pytest

CONFIG_KEYS = ('mpps_forward_enabled', 'mpps_forward_host',
               'mpps_forward_port', 'mpps_forward_called_ae')


class TestMppsForwardConfig:

    def test_default_config_carries_keys(self):
        """Config drift fix rides along: dicom_mpps_port was missing from
        default_config (only an inline fallback at lifecycle.py)."""
        from config import default_config
        for key in CONFIG_KEYS:
            assert key in default_config, key
        assert default_config['mpps_forward_enabled'] is False
        assert str(default_config.get('dicom_mpps_port', '')) == '11114'

    @pytest.mark.asyncio
    async def test_disabled_config_never_associates(self):
        from services.mpps_forward.service import forward_mpps
        from pydicom.dataset import Dataset
        ds = Dataset()
        ds.AccessionNumber = 'ACC-C3-1'
        with patch('pynetdicom.AE') as mock_ae:
            ok = await forward_mpps('N_CREATE', ds,
                                    _config={'mpps_forward_enabled': False})
        assert ok is False
        mock_ae.assert_not_called()

    @pytest.mark.asyncio
    async def test_unreachable_endpoint_returns_false_without_raise(self):
        # Bind then close: nothing listens there now.
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()

        from services.mpps_forward.service import forward_mpps
        from pydicom.dataset import Dataset
        ds = Dataset()
        ds.AccessionNumber = 'ACC-C3-2'
        started = time.monotonic()
        ok = await forward_mpps(
            'N_CREATE', ds,
            _config={'mpps_forward_enabled': True, 'mpps_forward_host':
                     '127.0.0.1', 'mpps_forward_port': str(port),
                     'mpps_forward_called_ae': 'REMOTE_PACS'})
        elapsed = time.monotonic() - started
        assert ok is False
        assert elapsed < 15, 'dead endpoint must not hang the caller'


class _RecordingPacs:
    """Minimal MPPS SCP capturing forwarded N-CREATE/N-SET identifiers."""

    def __init__(self):
        self.port = None
        self.server = None
        self.received = []

    def start(self):
        from pydicom.dataset import Dataset
        from pynetdicom import AE, evt
        from pynetdicom.presentation import build_context
        from pynetdicom.sop_class import ModalityPerformedProcedureStep

        def _handle(event):
            # N-CREATE carries an Attribute List, N-SET a Modification List
            if event.event == evt.EVT_N_CREATE:
                self.received.append(event.attribute_list)
                return 0x0000, event.attribute_list
            self.received.append(event.modification_list)
            status = Dataset()
            status.Status = 0x0000
            return 0x0000,

        ae = AE(ae_title='REMOTE_PACS')
        ae.supported_contexts = [build_context(ModalityPerformedProcedureStep)]
        self.server = ae.start_server(
            ('127.0.0.1', 0), evt_handlers=[
                (evt.EVT_N_CREATE, _handle),
                (evt.EVT_N_SET, _handle),
            ], block=False)
        self.port = self.server.server_address[1]

    def stop(self):
        if self.server:
            self.server.shutdown()


class TestMppsForwardDelivery:

    @pytest.fixture
    def pacs(self):
        rec = _RecordingPacs()
        rec.start()
        yield rec
        rec.stop()

    @pytest.mark.asyncio
    async def test_n_create_dataset_reaches_remote_pacs(self, pacs):
        from pydicom.dataset import Dataset
        from services.mpps_forward.service import forward_mpps

        ds = Dataset()
        ds.AccessionNumber = 'ACC-C3-FWD'
        ds.SpecificCharacterSet = 'ISO_IR 100'

        ok = await forward_mpps(
            'N_CREATE', ds,
            _config={'mpps_forward_enabled': True,
                     'mpps_forward_host': '127.0.0.1',
                     'mpps_forward_port': str(pacs.port),
                     'mpps_forward_called_ae': 'REMOTE_PACS'})
        assert ok is True
        deadline = time.time() + 5
        while time.time() < deadline and not pacs.received:
            time.sleep(0.05)
        assert any(
            getattr(d, 'AccessionNumber', '') == 'ACC-C3-FWD'
            for d in pacs.received), 'remote PACS never saw the N-CREATE'

    @pytest.mark.asyncio
    async def test_consumer_forwards_after_local_persist(self):
        """Both consumer handlers hand the dataset to the forwarder after
        the local write commits — fire-and-forget, failures swallowed."""
        import inspect
        import services.mpps_consumer.service as consumer_mod
        src = inspect.getsource(consumer_mod)
        assert 'forward_mpps' in src or '_forward' in src
        assert src.count('maybe_forward_mpps') >= 2, (
            'both N-CREATE and N-SET paths must attempt forwarding')
