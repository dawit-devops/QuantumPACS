"""M-5: AE thread entrypoints must not crash when the DICOM event loop is
missing or closed — association threads can outlive the loop (shutdown
race, startup failure) and a bare run_coroutine_threadsafe would raise
RuntimeError inside the pynetdicom thread."""
from unittest.mock import MagicMock, patch

from pydicom.dataset import Dataset

from dcm.server import handle_find, handle_n_create, handle_n_set, handle_store


def _mwl_event():
    event = MagicMock()
    event.identifier = Dataset()
    event.context = MagicMock()
    event.context.abstract_syntax = ''
    return event


class TestLoopUnavailableGuard:
    def test_handle_find_returns_a700_when_loop_missing(self):
        with patch('dcm.server._loop', None):
            statuses = [s for s, _ in handle_find(_mwl_event())]
        assert statuses == [0xA700]

    def test_handle_find_returns_a700_when_loop_closed(self):
        event = _mwl_event()

        def _raise(coro, loop):
            coro.close()
            raise RuntimeError('Event loop is closed')

        with patch('dcm.server.asyncio.run_coroutine_threadsafe',
                   side_effect=_raise):
            with patch('dcm.server._loop'):
                statuses = [s for s, _ in handle_find(event)]
        assert statuses == [0xA700]

    def test_handle_n_create_returns_0110_when_loop_missing(self):
        with patch('dcm.server._loop', None):
            status = handle_n_create(_mwl_event())
        assert status == 0x0110

    def test_handle_n_set_returns_0110_when_loop_missing(self):
        with patch('dcm.server._loop', None):
            status = handle_n_set(_mwl_event())
        assert status == 0x0110

    def test_handle_store_returns_failure_when_loop_missing(self):
        event = MagicMock()
        with patch('dcm.server._loop', None):
            status = handle_store(event)
        assert status == 0x0001
