import asyncio
import ipaddress
import signal
import traceback
import uuid
from io import BytesIO

from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import (
    ModalityWorklistInformationFind,
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelFind,
)

from dcm.store import store_instance, tenant_db_scope, resolve_tenant_slug_for_ae, TenantResolutionError
from config import config
from lifecycle import setup, teardown
from log import get_logger

log = get_logger(__name__)

_initialized = False
_init_lock = asyncio.Lock()


def _requestor_ae_title(event):
    """Calling AE title of the association that raised `event` (CR-02)."""
    assoc = getattr(event, 'assoc', None)
    requestor = getattr(assoc, 'requestor', None) if assoc else None
    return getattr(requestor, 'ae_title', '') or ''


def _reject_unmapped_ae():
    """True when multi-tenant AE gating is active (G-1).

    Both an explicit AE->tenant map and the opt-in reject flag must be set:
    with no map there is nothing to reject against, so the historical
    single-tenant fallback to the default tenant stays in effect.
    """
    raw_map = (config.get('dicom_ae_tenant_map', '') or '').strip()
    return (
        config.get('dicom_reject_unmapped_ae', 'false') == 'true'
        and bool(raw_map)
    )


async def _tenant_scope_for_ae(ae_title):
    """Resolve the tenant scope for a DICOM calling AE (CR-02).

    Returns (tenant_slug, tenant_info) — ('', {}) for unmapped AEs, which
    fall back to the seeded `default` tenant whose data store is the main
    database. A mapped AE whose tenant is missing from the registry raises
    TenantResolutionError (ME-05): silently serving the default scope would
    leak the default tenant's data to a tenant's modality.

    When multi-tenant gating is active (dicom_reject_unmapped_ae), an AE that
    is not present in the map is refused (G-1) rather than routed to the
    default tenant. The association layer enforces this pre-acceptance via
    ae.require_calling_aet; this guard is defense-in-depth so an unmapped AE
    can never reach the default scope through any tenant-resolution path.
    """
    slug = resolve_tenant_slug_for_ae(ae_title)
    if not slug or slug == 'default':
        if _reject_unmapped_ae():
            raise TenantResolutionError(
                f"Calling AE {ae_title!r} is not mapped to any tenant"
            )
        return '', {}
    from db.conn import get_conn
    from db.tenants import Tenants
    async with get_conn() as conn:
        info = await Tenants(conn).get_by_slug(slug) or {}
    if not info:
        raise TenantResolutionError(f'Tenant {slug!r} not found in registry')
    return slug, info


async def store(ds, data, ae_title=''):
    global _initialized

    if not _initialized:
        async with _init_lock:
            if not _initialized:
                await setup()
                _initialized = True

    return await store_instance(ds, data, ae_title=ae_title)


async def _handle_store_async(ds, dst, ae_title=''):
    try:
        return await store(ds, dst, ae_title=ae_title)
    except Exception:
        log.error('DICOM store failed: %s', traceback.format_exc())
        return False


def _submit(coro, timeout):
    """Run a coroutine on the DICOM loop from a pynetdicom thread.

    M-5: association threads can outlive the loop (shutdown race,
    startup failure) — guard the submit so a missing/closed loop yields
    None instead of raising RuntimeError inside the pynetdicom thread.
    The caller maps None to the appropriate failure status.
    """
    if _loop is None:
        coro.close()
        log.error('DICOM event loop not running; dropping %s',
                  getattr(coro, '__qualname__', type(coro).__name__))
        return None
    try:
        future = asyncio.run_coroutine_threadsafe(coro, _loop)
    except RuntimeError:
        coro.close()
        log.error('DICOM event loop unavailable; dropping %s',
                  getattr(coro, '__qualname__', type(coro).__name__))
        return None
    return future.result(timeout=timeout)


def handle_store(event):
    ds = event.dataset
    ds.file_meta = event.file_meta
    dst = BytesIO()

    try:
        ds.save_as(dst, enforce_file_format=False)
    except Exception:
        log.error('DICOM save failed: %s', traceback.format_exc())
        return 0x0001

    try:
        result = _submit(
            _handle_store_async(ds, dst, _requestor_ae_title(event)), 60,
        )
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


async def handle_find_async(query_ds, ae_title=''):
    try:
        slug, tenant_info = await _tenant_scope_for_ae(ae_title)
    except TenantResolutionError:
        raise
    # S2-02 refined: C-FINDs arrive over pynetdicom, not HTTP, so
    # TenantMiddleware never sees them — meter here against the resolved
    # tenant instead of relying on the shared api_calls counter.
    if slug:
        try:
            from db.metering import record_mwl_query
            await record_mwl_query(slug)
        except Exception:
            pass
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
            filters['accession'] = str(query_ds.AccessionNumber)

        # Worklist entries are per-tenant: a mapped AE queries its own
        # tenant's scheduled exams (CR-02).
        async with tenant_db_scope(slug, tenant_info):
            async with get_conn() as conn:
                # M-8: page the C-FIND instead of one 1000-row query — a
                # monolithic fetch plus the 30s SCP timeout blocks the
                # modality on slow datasets. Each page is bounded, the
                # first page returns promptly, and the cap keeps a runaway
                # dataset from starving the loop.
                per_page = 250
                entries = []
                for page in range(1, 9):
                    # search() returns (rows, total) — the tuple must be
                    # unpacked or the caller iterates a 2-tuple and crashes
                    # (seen as empty MWL).
                    rows, _ = await Worklist(conn).search(
                        status='scheduled', per_page=per_page, page=page,
                        **filters)
                    entries.extend(rows)
                    if len(rows) < per_page:
                        break

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
    # CR-1: manual tracking states (arrived/completed) are distinct from the
    # MPPS-driven `performed` — map each to its DICOM SPS status instead of
    # silently falling back to SCHEDULED.
    sps_ds.ScheduledProcedureStepStatus = {
        'scheduled': 'SCHEDULED',
        'arrived': 'ARRIVED',
        'in_progress': 'STARTED',
        'performed': 'COMPLETED',
        'completed': 'COMPLETED',
        'cancelled': 'CANCELLED',
    }.get(entry.get('status', ''), 'SCHEDULED')
    ds.ScheduledProcedureStepSequence = [sps_ds]

    ds.file_meta = Dataset()
    ds.file_meta.MediaStorageSOPClassUID = ModalityWorklistInformationFind
    # M-6: the id column is a UUID, but MediaStorageSOPInstanceUID must be
    # a valid DICOM UID — a hyphenated UUID string is illegal (only digits
    # and dots, <= 64 chars). Map UUIDs through the RFC 4122 2.25 root
    # (2.25.<decimal 128-bit value>), which is the canonical DICOM mapping.
    entry_id = entry.get('id', '') or ''
    if isinstance(entry_id, uuid.UUID):
        ds.file_meta.MediaStorageSOPInstanceUID = '2.25.' + str(entry_id.int)
    else:
        ds.file_meta.MediaStorageSOPInstanceUID = str(entry_id)
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    return ds


async def handle_find_qr_async(query_ds, ae_title=''):
    """Patient/Study Root Q/R C-FIND: study-, series- or instance-level."""
    try:
        slug, tenant_info = await _tenant_scope_for_ae(ae_title)
    except TenantResolutionError:
        raise
    try:
        from db.conn import get_conn
        from db.query_retrieve import QueryRetrieve

        # Studies are per-tenant: a mapped AE queries its own tenant's data
        # (CR-02); unmapped AEs read the default tenant (main store).
        async with tenant_db_scope(slug, tenant_info):
            async with get_conn() as conn:
                return await QueryRetrieve(query_ds).search(conn)
    except Exception:
        log.error('Q/R C-FIND failed: %s', traceback.format_exc())
        return []


def handle_find(event):
    query_ds = event.identifier
    ae_title = _requestor_ae_title(event)
    # EVT_C_FIND carries both the MWL and the Q/R models — dispatch on the
    # negotiated abstract syntax of the presentation context.
    abstract = getattr(getattr(event, 'context', None), 'abstract_syntax', '')
    if abstract in (
        PatientRootQueryRetrieveInformationModelFind,
        StudyRootQueryRetrieveInformationModelFind,
    ):
        coro = handle_find_qr_async(query_ds, ae_title)
    else:
        coro = handle_find_async(query_ds, ae_title)

    try:
        results = _submit(coro, 30)
    except TenantResolutionError as e:
        # ME-05: a mapped AE whose tenant is missing must not be served the
        # default tenant's data — refuse the query loudly instead.
        log.error('C-FIND refused: %s', e)
        yield 0xA700, None
        return
    except Exception:
        log.error('C-FIND timed out or failed: %s', traceback.format_exc())
        yield 0xA700, None
        return
    if results is None:
        yield 0xA700, None
        return

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

    # G-1: when multi-tenant AE gating is active, only calling AEs present in
    # the AE->tenant map may associate. pynetdicom rejects the association
    # pre-acceptance for any AE outside this set, so an unmapped modality
    # can never reach the default tenant's store.
    if _reject_unmapped_ae():
        mapped_aets = [
            pair.split(':', 1)[0].strip()
            for pair in (config.get('dicom_ae_tenant_map') or '').split(',')
            if ':' in pair and pair.strip()
        ]
        if mapped_aets:
            preset = ae.require_calling_aet
            if isinstance(preset, (list, set, tuple)):
                mapped_aets = list(dict.fromkeys(list(preset) + mapped_aets))
            ae.require_calling_aet = mapped_aets


async def _run_mpps_async(fn, event):
    """Run an MPPS consumer call inside the calling AE's tenant scope.

    CR-3: N-CREATE/N-SET arrive on the DICOM association outside the HTTP
    middleware that sets the per-request tenant scope, so — exactly like
    C-FIND (handle_find_async) — the tenant must be resolved from the AE
    title and the consumer run inside tenant_db_scope. Otherwise every
    MPPS event is stamped with the `default` tenant even when the
    modality belongs to another tenant.
    """
    slug, tenant_info = await _tenant_scope_for_ae(_requestor_ae_title(event))
    async with tenant_db_scope(slug, tenant_info):
        return await fn(event)


def _run_mpps(handler_name, fn, event):
    try:
        result = _submit(_run_mpps_async(fn, event), 30)
    except TenantResolutionError as e:
        # ME-05: a mapped AE whose tenant is missing must not be served the
        # default tenant's data — refuse the request loudly instead.
        log.error('MPPS %s refused: %s', handler_name, e)
        return 0xA700
    except Exception:
        log.error('MPPS %s failed: %s', handler_name, traceback.format_exc())
        return 0x0110  # Processing failure
    if result is None:
        return 0x0110  # Loop unavailable — processing failure
    if not result:
        return 0x0112  # No such object instance (unknown accession)
    return 0x0000  # Success


# MPPS N-CREATE handler (S6-07)
def handle_n_create(event):
    """MPPS N-CREATE: modality starts performing a procedure."""
    from services.mpps_consumer.service import MppsConsumer
    return _run_mpps('N-CREATE', MppsConsumer().handle_n_create, event)


# MPPS N-SET handler (S6-07)
def handle_n_set(event):
    """MPPS N-SET: modality completes or cancels a procedure."""
    from services.mpps_consumer.service import MppsConsumer
    return _run_mpps('N-SET', MppsConsumer().handle_n_set, event)


handlers = [
    (evt.EVT_C_STORE, handle_store),
    (evt.EVT_C_FIND, handle_find),
    (evt.EVT_N_CREATE, handle_n_create),
    (evt.EVT_N_SET, handle_n_set),
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
