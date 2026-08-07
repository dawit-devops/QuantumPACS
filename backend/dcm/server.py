import asyncio
import ipaddress
import signal
import traceback
from io import BytesIO

from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import (
    ModalityWorklistInformationFind,
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelFind,
)

from dcm.store import store_instance
from config import config
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
    except Exception:
        log.error('DICOM store failed: %s', traceback.format_exc())
        return False


def handle_store(event):
    ds = event.dataset
    ds.file_meta = event.file_meta
    dst = BytesIO()

    try:
        ds.save_as(dst, enforce_file_format=False)
    except Exception:
        log.error('DICOM save failed: %s', traceback.format_exc())
        return 0x0001

    future = asyncio.run_coroutine_threadsafe(_handle_store_async(ds, dst), _loop)
    try:
        result = future.result(timeout=60)
    except Exception:
        log.error('DICOM store timed out or failed: %s', traceback.format_exc())
        return 0x0001

    if not result:
        return 0x0001

    return 0x0000


def _mwl_like(value):
    """Translate DICOM C-FIND wildcards to SQL LIKE patterns.

    DICOM matching allows '*' (any sequence) and '?' (single char). Literal
    '%'/'_' in query values would otherwise inject pattern syntax, so they
    are stripped before mapping.
    """
    return value.replace('%', '').replace('_', '').replace('*', '%').replace('?', '_')


def _mwl_range(value):
    """Split a DICOM range value ('20260701-20260731') into (low, high)."""
    if '-' in value:
        low, _, high = value.partition('-')
        return low or None, high or None
    return value, value


def _fmt_date(value):
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y%m%d')
    return str(value).replace('-', '')


def _fmt_time(value):
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%H%M%S')
    return str(value).replace(':', '')


async def handle_find_async(query_ds):
    try:
        from db.conn import get_conn
        from db.worklist import Worklist

        filters = {}
        # Raw values only — Worklist.search() translates DICOM wildcards to
        # SQL LIKE itself. Pre-translating here would double-escape the '%'.
        if hasattr(query_ds, 'PatientID') and query_ds.PatientID:
            filters['patient_id'] = str(query_ds.PatientID)
        if hasattr(query_ds, 'PatientName') and query_ds.PatientName:
            filters['patient_name'] = str(query_ds.PatientName)
        if hasattr(query_ds, 'Modality') and query_ds.Modality:
            filters['modality'] = str(query_ds.Modality)
        if hasattr(query_ds, 'RequestedProcedureID') and query_ds.RequestedProcedureID:
            filters['requested_procedure_id'] = str(query_ds.RequestedProcedureID)
        if hasattr(query_ds, 'ScheduledProcedureStepSequence') and query_ds.ScheduledProcedureStepSequence:
            sps = query_ds.ScheduledProcedureStepSequence[0]
            if hasattr(sps, 'ScheduledStationAETitle') and sps.ScheduledStationAETitle:
                filters['station_ae_title'] = str(sps.ScheduledStationAETitle)
            if hasattr(sps, 'ScheduledProcedureStepStartDate') and sps.ScheduledProcedureStepStartDate:
                date_from, date_to = _mwl_range(str(sps.ScheduledProcedureStepStartDate))
                filters['date_from'] = date_from
                filters['date_to'] = date_to
            if hasattr(sps, 'ScheduledProcedureStepStartTime') and sps.ScheduledProcedureStepStartTime:
                time_from, time_to = _mwl_range(str(sps.ScheduledProcedureStepStartTime))
                filters['time_from'] = time_from
                filters['time_to'] = time_to
            if hasattr(sps, 'Modality') and sps.Modality and 'modality' not in filters:
                filters['modality'] = str(sps.Modality)
        if hasattr(query_ds, 'AccessionNumber') and query_ds.AccessionNumber:
            filters['search'] = str(query_ds.AccessionNumber)

        async with get_conn() as conn:
            # search() returns (rows, total) — the tuple must be unpacked or
            # the caller iterates a 2-tuple and crashes (seen as empty MWL).
            entries, _ = await Worklist(conn).search(status='scheduled', per_page=1000, **filters)

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
    ds.ReferringPhysicianName = entry.get('referring_physician', '') or ''
    ds.RequestingPhysician = entry.get('requesting_physician', '') or ''
    ds.StudyInstanceUID = entry.get('study_uid', '') or ''
    ds.RequestedProcedureID = entry.get('requested_procedure_id', '') or ''
    ds.RequestedProcedureDescription = entry.get('requested_procedure_desc', '') or ''
    ds.RequestedProcedurePriority = entry.get('requested_procedure_priority', '') or ''
    # Universal service ID from the ORM OBR-4 components (ME-03): emitted as
    # a code sequence only when a code value was actually captured.
    if entry.get('requested_procedure_code'):
        code_ds = Dataset()
        code_ds.CodeValue = entry.get('requested_procedure_code', '') or ''
        code_ds.CodingSchemeDesignator = entry.get('requested_procedure_code_scheme', '') or ''
        code_ds.CodeMeaning = entry.get('requested_procedure_code_meaning', '') or ''
        ds.RequestedProcedureCodeSequence = [code_ds]

    sps_ds = Dataset()
    sps_ds.Modality = entry.get('modality', '') or ''
    sps_ds.ScheduledStationAETitle = entry.get('station_ae_title', '') or ''
    sps_ds.ScheduledStationName = entry.get('scheduled_station_name', '') or ''
    # asyncpg returns DATE/TIME columns as date/time objects — str() would
    # emit '2026-07-25'/'10:30:00', which is not valid DICOM (YYYYMMDD/HHMMSS).
    sps_ds.ScheduledProcedureStepStartDate = _fmt_date(entry.get('scheduled_date', ''))
    sps_ds.ScheduledProcedureStepStartTime = _fmt_time(entry.get('scheduled_time', ''))
    sps_ds.ScheduledPerformingPhysicianName = entry.get('scheduled_performing_physician', '') or ''
    sps_ds.ScheduledProcedureStepDescription = entry.get('requested_procedure_desc', '') or ''
    sps_ds.ScheduledProcedureStepID = entry.get('scheduled_procedure_step_id', '') or ''
    sps_ds.ProtocolName = entry.get('protocol_name', '') or ''
    # (0040,1002) Reason for the Requested Procedure lives inside the SPS.
    sps_ds.ReasonForTheRequestedProcedure = entry.get('reason_for_requested_procedure', '') or ''
    sps_ds.ScheduledProcedureStepStatus = {
        'scheduled': 'SCHEDULED',
        'in_progress': 'STARTED',
        'performed': 'COMPLETED',
        'cancelled': 'CANCELLED',
    }.get(entry.get('status', ''), 'SCHEDULED')
    ds.ScheduledProcedureStepSequence = [sps_ds]

    ds.file_meta = Dataset()
    ds.file_meta.MediaStorageSOPClassUID = ModalityWorklistInformationFind
    # The id column is a UUID — asyncpg returns a uuid.UUID object which
    # pydicom UID() refuses ("A UID must be created from a string").
    ds.file_meta.MediaStorageSOPInstanceUID = str(entry.get('id', '') or '')
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    return ds


async def handle_find_qr_async(query_ds):
    """Patient/Study Root Q/R C-FIND: study-, series- or instance-level."""
    try:
        from db.conn import get_conn
        from db.query_retrieve import QueryRetrieve

        async with get_conn() as conn:
            return await QueryRetrieve(query_ds).search(conn)
    except Exception:
        log.error('Q/R C-FIND failed: %s', traceback.format_exc())
        return []


def handle_find(event):
    query_ds = event.identifier
    # EVT_C_FIND carries both the MWL and the Q/R models — dispatch on the
    # negotiated abstract syntax of the presentation context.
    abstract = getattr(getattr(event, 'context', None), 'abstract_syntax', '')
    if abstract in (
        PatientRootQueryRetrieveInformationModelFind,
        StudyRootQueryRetrieveInformationModelFind,
    ):
        coro = handle_find_qr_async(query_ds)
    else:
        coro = handle_find_async(query_ds)

    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    try:
        results = future.result(timeout=30)
    except Exception:
        log.error('C-FIND timed out or failed: %s', traceback.format_exc())
        return 0xA700

    for ds in results:
        yield 0xFF00, ds

    yield 0x0000, None


def _ip_allowed(address, allowed):
    try:
        addr = ipaddress.ip_address(address)
    except ValueError:
        return False
    for entry in allowed:
        try:
            net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if addr in net:
            return True
    return False


def _handle_accept(event):
    """EVT_ACCEPTED — abort associations from hosts outside the IP allowlist.

    AE-title gating is enforced natively via ``ae.require_calling_aet``
    (configured in lifecycle/main); pynetdicom has no pre-acceptance event,
    so the IP check runs here — aborting immediately after acceptance still
    prevents any C-STORE/C-FIND exchange with non-allowlisted hosts. Both
    lists default to empty (allow all) so local dev flows are unchanged.
    """
    allowed_ips = [s.strip() for s in (config.get('dicom_allowed_ips') or '').split(',') if s.strip()]
    if not allowed_ips:
        return
    requestor = event.assoc.requestor
    address = (requestor.address or '').split(':')[0]
    if not _ip_allowed(address, allowed_ips):
        log.warning('DICOM association aborted: caller %s not in IP allowlist', address)
        event.assoc.abort()


def apply_association_policy(ae):
    """Apply AE-title/called-AE restrictions to an AE from config.

    Empty dicom_aet_allowed accepts any calling AE title; when set, the
    association is rejected pre-acceptance by pynetdicom.
    """
    if config.get('dicom_require_called_aet', 'false') == 'true':
        ae.require_called_aet = True
    allowed_aets = [s.strip() for s in (config.get('dicom_aet_allowed') or '').split(',') if s.strip()]
    if allowed_aets:
        ae.require_calling_aet = allowed_aets


handlers = [
    (evt.EVT_C_STORE, handle_store),
    (evt.EVT_C_FIND, handle_find),
    (evt.EVT_ACCEPTED, _handle_accept),
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
    ae.ae_title = config.get('dicom_ae_title', 'QUANTUMPACS')
    ae.supported_contexts = StoragePresentationContexts
    apply_association_policy(ae)
    port = int(config.get('dicom_cstore_port', '11112'))
    _scp = ae.start_server(('', port), evt_handlers=handlers)
    _scp.blocking_run()
    _loop.close()
