import asyncio
import signal
import sys
import traceback
from io import BytesIO

from pynetdicom import AE, evt, StoragePresentationContexts

from dcm.file import get_meta
from dcm.store import store_instance
from lifecycle import setup, teardown
from log import get_logger

log = get_logger(__name__)

_initialized = False
_init_lock = asyncio.Lock()


async def store(ds, data):
    global _initialized

    if not _initialized:
        async with _init_lock:
            if not _initialized:
                await setup()
                _initialized = True

    return await store_instance(ds, data)


async def _handle_store_async(ds, dst):
    try:
        return await store(ds, dst)
    except Exception as e:
        log.error('DICOM store failed: %s', traceback.format_exc())
        return False


def handle_store(event):
    ds = event.dataset
    ds.file_meta = event.file_meta
    dst = BytesIO()

    try:
        ds.save_as(dst, write_like_original=False)
    except Exception as e:
        log.error('DICOM save failed: %s', traceback.format_exc())
        return 0x0001

    future = asyncio.run_coroutine_threadsafe(_handle_store_async(ds, dst), _loop)
    try:
        result = future.result(timeout=60)
    except Exception as e:
        log.error('DICOM store timed out or failed: %s', traceback.format_exc())
        return 0x0001

    if not result:
        return 0x0001

    return 0x0000


handlers = [(evt.EVT_C_STORE, handle_store)]
_scp = None
_loop = None


async def _async_shutdown():
    await teardown()
    if _scp:
        _scp.shutdown()


def _signal_handler(sig, frame):
    if _loop and not _loop.is_closed():
        asyncio.run_coroutine_threadsafe(_async_shutdown(), _loop)


def main():
    global _scp, _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    signal.signal(signal.SIGINT, _signal_handler)
    ae = AE()
    ae.supported_contexts = StoragePresentationContexts
    _scp = ae.start_server(('', 11112), evt_handlers=handlers)
    _scp.blocking_run()
    _loop.close()
