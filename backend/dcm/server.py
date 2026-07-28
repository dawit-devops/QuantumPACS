import asyncio
import signal
import sys
import traceback
from io import BytesIO

from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import ModalityWorklistInformationFind

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
        ds.save_as(dst, enforce_file_format=False)
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


async def handle_find_async(query_ds):
    try:
        from db.conn import get_conn
        from db.worklist import Worklist

        filters = {}
        if hasattr(query_ds, 'PatientID') and query_ds.PatientID:
            filters['search'] = str(query_ds.PatientID)
        if hasattr(query_ds, 'Modality') and query_ds.Modality:
            filters['modality'] = str(query_ds.Modality)
        if hasattr(query_ds, 'ScheduledProcedureStepSequence') and query_ds.ScheduledProcedureStepSequence:
            sps = query_ds.ScheduledProcedureStepSequence[0]
            if hasattr(sps, 'ScheduledStationAETitle') and sps.ScheduledStationAETitle:
                filters['station_ae_title'] = str(sps.ScheduledStationAETitle)
            if hasattr(sps, 'ScheduledProcedureStepStartDate') and sps.ScheduledProcedureStepStartDate:
                filters['date_from'] = str(sps.ScheduledProcedureStepStartDate)
                filters['date_to'] = str(sps.ScheduledProcedureStepStartDate)
            if hasattr(sps, 'Modality') and sps.Modality and 'modality' not in filters:
                filters['modality'] = str(sps.Modality)
        if hasattr(query_ds, 'AccessionNumber') and query_ds.AccessionNumber:
            filters['search'] = filters.get('search', str(query_ds.AccessionNumber))

        async with get_conn() as conn:
            entries = await Worklist(conn).search(status='scheduled', per_page=1000, **filters)

        results = []
        for entry in entries:
            rsp = _entry_to_dataset(entry)
            if rsp:
                results.append(rsp)
        return results
    except Exception:
        log.error('MWL C-FIND failed: %s', traceback.format_exc())
        return []


def _entry_to_dataset(entry):
    from pydicom.dataset import Dataset
    from pydicom.uid import ExplicitVRLittleEndian

    ds = Dataset()
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.AccessionNumber = entry.get('accession_number', '') or ''
    ds.PatientName = entry.get('patient_name', '') or ''
    ds.PatientID = entry.get('patient_id', '') or ''
    ds.PatientBirthDate = entry.get('patient_birth_date', '') or ''
    ds.PatientSex = entry.get('patient_sex', '') or ''
    ds.ReferringPhysicianName = ''
    ds.RequestingPhysician = ''
    ds.StudyInstanceUID = entry.get('study_uid', '') or ''
    ds.RequestedProcedureID = entry.get('requested_procedure_id', '') or ''
    ds.RequestedProcedureDescription = entry.get('requested_procedure_desc', '') or ''

    sps_ds = Dataset()
    sps_ds.Modality = entry.get('modality', '') or ''
    sps_ds.ScheduledStationAETitle = entry.get('station_ae_title', '') or ''
    sps_ds.ScheduledProcedureStepStartDate = str(entry.get('scheduled_date', '') or '')
    sps_ds.ScheduledProcedureStepStartTime = str(entry.get('scheduled_time', '') or '')
    sps_ds.ScheduledPerformingPhysicianName = ''
    sps_ds.ScheduledProcedureStepDescription = entry.get('requested_procedure_desc', '') or ''
    ds.ScheduledProcedureStepSequence = [sps_ds]

    ds.file_meta = Dataset()
    ds.file_meta.MediaStorageSOPClassUID = ModalityWorklistInformationFind
    ds.file_meta.MediaStorageSOPInstanceUID = entry.get('id', '') or ''
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    return ds


def handle_find(event):
    query_ds = event.identifier

    future = asyncio.run_coroutine_threadsafe(handle_find_async(query_ds), _loop)
    try:
        results = future.result(timeout=30)
    except Exception:
        log.error('MWL C-FIND timed out or failed: %s', traceback.format_exc())
        return 0xA700

    for ds in results:
        yield 0xFF00, ds

    yield 0x0000, None


def handle_move(event):
    log.warning('C-MOVE received but not fully implemented')
    return 0x0000


def handle_get(event):
    log.warning('C-GET received but not fully implemented')
    return 0x0000


handlers = [
    (evt.EVT_C_STORE, handle_store),
    (evt.EVT_C_FIND, handle_find),
    (evt.EVT_C_MOVE, handle_move),
    (evt.EVT_C_GET, handle_get),
]
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
