"""MWL-RS mirror sync worker (ADR-028 Phase 3).

When the DICOMweb proxy is enabled (`dicom_proxy=true`) modalities are
served by the dcm4chee archive, so QuantumPACS mirrors its `worklist_entries`
into the archive via MWL-RS — otherwise modality worklist queries against
dcm4chee return nothing. A background thread (started in lifecycle.py) polls
for dirty rows and replays create/status/delete against the archive.

dcm4chee specifics discovered live (2026-08-15):
- `POST /aets/{ae}/rs/patients` must precede `POST .../mwlitems`: the
  archive links MWL items to existing patients. The call is an upsert.
- `POST .../mwlitems` honors a top-level StudyInstanceUID in the payload and
  is an upsert on it, so the worker derives a deterministic UID from the row
  (tenant|patient|accession|SPS id). Without a top-level UID the archive
  generates a fresh random one per POST, which would duplicate items on
  every re-push.
- Status values are SCHEDULED|ARRIVED|READY|STARTED|DEPARTED|CANCELED|
  DISCONTINUED|COMPLETED (there is no "IN PROGRESS" — the ADR's mapping is
  realised as STARTED).
- Cancel mirrors as DELETE /mwlitems/{uid}/{spsID} (204; 404 = already gone).

Tenant scoping is deliberately NOT applied (ADR-028 R7): dcm4chee is a
single global archive, same as the DICOMweb proxy.
"""
import threading
import time

import httpx
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

from api.dicomweb_proxy import proxy_enabled
from config import config
from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)

# QP status -> dcm4chee MWL-RS status (cancelled mirrors as DELETE instead).
STATUS_MAP = {
    'scheduled': 'SCHEDULED',
    'in_progress': 'STARTED',
    'performed': 'COMPLETED',
}

_DIRTY_SQL = """
SELECT * FROM worklist_entries
WHERE mwl_synced_at IS NULL
   OR mwl_synced_at < updated_at
   OR mwl_sync_error != ''
ORDER BY updated_at
LIMIT 100
"""


def mwl_sync_enabled():
    return proxy_enabled()


def _dicom_date(value):
    if not value:
        return ''
    return str(value).replace('-', '').replace(':', '').strip()[:8]


def _dicom_time(value):
    if not value:
        return ''
    return str(value).replace(':', '').replace('.', '').strip()[:6]


def _clean_error(text):
    """Cap and strip control characters so nothing hostile lands in the row
    (same rationale as api.client.sanitizeMessage on the frontend)."""
    cleaned = ''.join(ch if ord(ch) >= 32 and ch != '\x7f' else ' ' for ch in str(text))
    return ' '.join(cleaned.split())[:240]


def mwl_uid(row):
    """Deterministic archive-side StudyInstanceUID for a worklist row.

    Stable across worker cycles so MWL-RS POST upserts and status/DELETE
    calls always hit the same item. Includes the row's primary key as
    fallback entropy so rows without accession/SPS id still get unique UIDs.
    """
    entropy = '|'.join([
        str(row.get('tenant_id') or 'default'),
        str(row.get('patient_id') or ''),
        str(row.get('accession_number') or ''),
        str(row.get('scheduled_procedure_step_id') or str(row.get('id'))),
    ])
    return generate_uid(entropy_srcs=[entropy])


def _mwl_dataset(row):
    ds = Dataset()
    ds.PatientName = row.get('patient_name') or row.get('patient_id')
    ds.PatientID = row.get('patient_id')
    sex = (row.get('patient_sex') or '').strip()
    if sex:
        ds.PatientSex = sex[0].upper()
    dob = _dicom_date(row.get('patient_birth_date'))
    if dob:
        ds.PatientBirthDate = dob
    if row.get('accession_number'):
        ds.AccessionNumber = row['accession_number']
    if row.get('requesting_physician'):
        ds.RequestingPhysician = row['requesting_physician']
    ds.StudyInstanceUID = mwl_uid(row)

    step = Dataset()
    step.Modality = row.get('modality') or ''
    step.ScheduledStationAETitle = row.get('station_ae_title') or ''
    if row.get('scheduled_station_name'):
        step.ScheduledStationName = row['scheduled_station_name']
    start_date = _dicom_date(row.get('scheduled_date'))
    if start_date:
        step.ScheduledProcedureStepStartDate = start_date
    start_time = _dicom_time(row.get('scheduled_time'))
    if start_time:
        step.ScheduledProcedureStepStartTime = start_time
    step.ScheduledProcedureStepID = (
        row.get('scheduled_procedure_step_id') or str(row.get('id'))[:16]
    )
    desc = row.get('protocol_name') or row.get('requested_procedure_desc') or ''
    if desc:
        step.ScheduledProcedureStepDescription = desc
    step.StudyInstanceUID = ds.StudyInstanceUID
    ds.ScheduledProcedureStepSequence = [step]
    return ds


class MwlSyncClient:
    """Thin MWL-RS client mirroring the DICOMweb proxy's httpx usage
    (manual client, closed explicitly — never an `async with` that could
    close mid-stream)."""

    def __init__(self):
        base = str(config.get('dcm4chee_url', 'http://localhost:8082/dcm4chee-arc')).rstrip('/')
        ae = config.get('dcm4chee_ae', 'DCM4CHEE')
        self.rs_base = f'{base}/aets/{ae}/rs'
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10, read=60, write=60, pool=60))

    async def aclose(self):
        await self.client.aclose()

    async def ensure_patient(self, row):
        ds = Dataset()
        ds.PatientName = row.get('patient_name') or row.get('patient_id')
        ds.PatientID = row.get('patient_id')
        sex = (row.get('patient_sex') or '').strip()
        if sex:
            ds.PatientSex = sex[0].upper()
        dob = _dicom_date(row.get('patient_birth_date'))
        if dob:
            ds.PatientBirthDate = dob
        resp = await self.client.post(
            f'{self.rs_base}/patients',
            content=ds.to_json(),
            headers={'Content-Type': 'application/dicom+json'},
        )
        if resp.status_code >= 300:
            raise RuntimeError(f'MWL patient create failed: HTTP {resp.status_code} {resp.text[:200]}')

    async def store(self, row):
        resp = await self.client.post(
            f'{self.rs_base}/mwlitems',
            content=_mwl_dataset(row).to_json(),
            headers={'Content-Type': 'application/dicom+json'},
        )
        if resp.status_code >= 300:
            raise RuntimeError(f'MWL store failed: HTTP {resp.status_code} {resp.text[:200]}')
        return mwl_uid(row)

    async def set_status(self, row, status):
        sps_id = row.get('scheduled_procedure_step_id') or str(row.get('id'))[:16]
        resp = await self.client.post(
            f'{self.rs_base}/mwlitems/{mwl_uid(row)}/{sps_id}/status/{status}',
        )
        if resp.status_code >= 300:
            raise RuntimeError(f'MWL status {status} failed: HTTP {resp.status_code} {resp.text[:200]}')

    async def remove(self, row):
        sps_id = row.get('scheduled_procedure_step_id') or str(row.get('id'))[:16]
        resp = await self.client.delete(
            f'{self.rs_base}/mwlitems/{mwl_uid(row)}/{sps_id}',
        )
        # 404 = item already gone (e.g. archive recreated); treat as success.
        if resp.status_code not in (200, 204, 404):
            raise RuntimeError(f'MWL delete failed: HTTP {resp.status_code} {resp.text[:200]}')


class MwlSyncer:
    """One sync pass: replay dirty rows to the archive, then record outcome."""

    async def run_once(self):
        if not mwl_sync_enabled():
            return None
        client = MwlSyncClient()
        stats = {'pushed': 0, 'status': 0, 'removed': 0, 'failed': 0}
        try:
            async with get_conn() as conn:
                rows = await conn.fetch(_DIRTY_SQL)
            for raw in rows:
                row = dict(raw)
                try:
                    await self._sync_row(client, row)
                    async with get_conn() as conn:
                        await conn.execute(
                            "UPDATE worklist_entries SET mwl_synced_at = now(), "
                            "mwl_sync_error = '' WHERE id = $1",
                            row['id'],
                        )
                        if row['status'] == 'cancelled':
                            stats['removed'] += 1
                        elif row['status'] == 'scheduled':
                            stats['pushed'] += 1
                        else:
                            stats['status'] += 1
                except Exception as e:
                    async with get_conn() as conn:
                        await conn.execute(
                            "UPDATE worklist_entries SET mwl_sync_error = $1 WHERE id = $2",
                            _clean_error(e), row['id'],
                        )
                    stats['failed'] += 1
                    log.warning('MWL sync failed for entry %s: %s', row['id'], e)
        finally:
            await client.aclose()
        if stats['pushed'] or stats['status'] or stats['removed'] or stats['failed']:
            log.info('MWL sync cycle: %s', stats)
        return stats

    async def _sync_row(self, client, row):
        if row['status'] == 'cancelled':
            await client.remove(row)
            return
        await client.ensure_patient(row)
        pushed = row.get('mwl_synced_at') is None or row['status'] == 'scheduled'
        if pushed:
            await client.store(row)
        status = STATUS_MAP.get(row['status'])
        if status and status != 'SCHEDULED':
            await client.set_status(row, status)


def _run_mwl_sync(loop):
    """Worker loop body (daemon thread). run_once is scheduled on the
    uvicorn main loop so the asyncpg pool / httpx clients stay on the loop
    that owns them (same constraint as the DICOM SCP thread)."""
    import asyncio

    interval = max(1, int(config.get('mwl_sync_interval', '10')))
    syncer = MwlSyncer()
    while True:
        if mwl_sync_enabled():
            try:
                if loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        syncer.run_once(), loop,
                    ).result(timeout=90)
                else:
                    asyncio.run(syncer.run_once())
            except Exception:
                log.warning('MWL sync cycle failed', exc_info=True)
        time.sleep(interval)


def start_mwl_sync():
    """Start the worker thread; no-op unless dicom_proxy=true."""
    if not mwl_sync_enabled():
        log.info('MWL-RS sync disabled (dicom_proxy=false)')
        return None
    try:
        import asyncio
        main_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_loop = None
    thread = threading.Thread(target=_run_mwl_sync, args=(main_loop,), daemon=True)
    thread.start()
    log.info('MWL-RS sync worker started (interval=%ss)', config.get('mwl_sync_interval', '10'))
    return thread