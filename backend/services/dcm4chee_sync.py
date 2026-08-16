"""dcm4chee → QuantumPACS self-heal sync worker (ADR-028 Phase 3).

When `dicom_proxy=true` modalities C-STORE to the dcm4chee archive (11112)
and the archive is expected to export each study back to the QuantumPACS
feed SCP (AE `QUANTUMPACS`, `dicom_cstore_port` 11113) so the metadata
pipeline (store_instance) keeps running. If the feed was down when a study
arrived — or the archive's export failed — QuantumPACS never sees it.

This worker closes that gap:

1. Poll the archive QIDO-RS for every StudyInstanceUID (paged).
2. Diff against the QuantumPACS `studies` table — the QP table *is* the
   watermark: any study the archive holds that QP does not know needs feeding.
3. Request the archive to export each missing study via the export REST API
   (`POST /aets/{ae}/dimse/{ae}/studies/{uid}/export/dicom:{feedAE}?queue=true`),
   which C-STOREs it to the QP feed SCP. `store_instance()`'s SOP-UID dedup
   makes re-exports idempotent.

Tenant scoping is intentionally NOT applied (ADR-028 R7) — the archive is a
single shared store, same as the DICOMweb proxy and MWL mirror.
"""
import threading
import time

import httpx

from api.dicomweb_proxy import proxy_enabled
from config import config
from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)

# QIDO-RS page size for the study-UID scan.
_PAGE = 100


def dcm4chee_sync_enabled():
    return proxy_enabled()


class Dcm4cheeSyncClient:
    """Thin QIDO-RS + export-REST client (same httpx usage as the proxy)."""

    def __init__(self):
        base = str(config.get('dcm4chee_url', 'http://localhost:8082/dcm4chee-arc')).rstrip('/')
        ae = config.get('dcm4chee_ae', 'DCM4CHEE')
        self.rs_base = f'{base}/aets/{ae}/rs'
        self.dimse_base = f'{base}/aets/{ae}/dimse'
        # Destination AE the archive C-STOREs exported studies to — the QP
        # feed SCP registered in the archive LDAP (docker/dcm4chee/ldif).
        self.feed_ae = config.get('dicom_ae_title', 'QUANTUMPACS')
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10, read=60, write=60, pool=60))

    async def aclose(self):
        await self.client.aclose()

    async def list_study_uids(self):
        """Page through QIDO-RS and return every StudyInstanceUID in the archive."""
        uids = []
        offset = 0
        while True:
            resp = await self.client.get(
                f'{self.rs_base}/studies',
                params={'includefield': '0020000D', 'limit': _PAGE, 'offset': offset},
            )
            if resp.status_code >= 300:
                raise RuntimeError(f'QIDO-RS failed: HTTP {resp.status_code} {resp.text[:200]}')
            # dcm4chee answers 204 No Content when a query matches nothing
            # (no JSON body), which must read as an empty page.
            if resp.status_code == 204 or not resp.content:
                break
            page = resp.json() or []
            for study in page:
                value = (study.get('0020000D') or {}).get('Value') or []
                if value:
                    uids.append(value[0])
            if len(page) < _PAGE:
                break
            offset += _PAGE
        return uids

    async def request_export(self, study_uid):
        """Ask the archive to C-STORE the study to the QP feed SCP (queued).

        PS3.18/export REST: POST /aets/{ae}/dimse/{movescp}/studies/{uid}/export/dicom:{dst}
        — `movescp` is the archive AE that performs the move; `queue=true`
        returns 202 (accepted) when the export is enqueued.
        """
        ae = config.get('dcm4chee_ae', 'DCM4CHEE')
        resp = await self.client.post(
            f'{self.dimse_base}/{ae}/studies/{study_uid}/export/dicom:{self.feed_ae}',
            params={'queue': 'true'},
        )
        if resp.status_code not in (200, 202):
            raise RuntimeError(f'export request failed: HTTP {resp.status_code} {resp.text[:200]}')


class Dcm4cheeSyncer:
    """One sync pass: scan the archive, feed every study QP does not know.

    A per-study cooldown watermark bounds re-requests for studies that never
    land in QP (feed SCP down / import failure). Without it, request_export
    returns 202 every cycle for the same study and the archive's export queue
    grows unboundedly. The in-flight guard prevents overlapping passes when a
    previous run exceeds the thread's 90 s wait (M3 in the phase review).
    """

    def __init__(self):
        self._cooldown = max(1, int(config.get('dcm4chee_sync_cooldown', '300')))
        self._last_requested = {}
        self._inflight = False

    async def run_once(self):
        if not dcm4chee_sync_enabled():
            return None
        if self._inflight:
            return None
        client = Dcm4cheeSyncClient()
        self._inflight = True
        stats = {'exported': 0, 'skipped': 0, 'failed': 0, 'cooldown': 0}
        try:
            uids = await client.list_study_uids()
            if not uids:
                return stats

            async with get_conn() as conn:
                rows = await conn.fetch(
                    'SELECT study_instance_uid FROM studies WHERE study_instance_uid = ANY($1)',
                    uids,
                )
            known = {row['study_instance_uid'] for row in rows}

            now = time.time()
            for uid in uids:
                if uid in known:
                    stats['skipped'] += 1
                    continue
                if now - self._last_requested.get(uid, 0) < self._cooldown:
                    stats['cooldown'] += 1
                    continue
                try:
                    await client.request_export(uid)
                    self._last_requested[uid] = now
                    stats['exported'] += 1
                except Exception as e:
                    stats['failed'] += 1
                    log.warning('dcm4chee sync export failed for study %s: %s', uid, e)
            # Bound memory: forget watermarks that are no longer in effect.
            stale = [uid for uid, ts in self._last_requested.items()
                     if now - ts >= self._cooldown * 2]
            for uid in stale:
                del self._last_requested[uid]
        finally:
            self._inflight = False
            await client.aclose()
        if stats['exported'] or stats['failed']:
            log.info('dcm4chee sync cycle: %s', stats)
        return stats


def _run_dcm4chee_sync(loop):
    """Worker loop body (daemon thread). run_once is scheduled on the uvicorn
    main loop so the asyncpg pool / httpx clients stay on the loop that owns
    them (same constraint as the MWL sync worker and DICOM SCP thread)."""
    import asyncio

    interval = max(1, int(config.get('dcm4chee_sync_interval', '30')))
    syncer = Dcm4cheeSyncer()
    while True:
        if dcm4chee_sync_enabled():
            try:
                if loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        syncer.run_once(), loop,
                    ).result(timeout=90)
                else:
                    asyncio.run(syncer.run_once())
            except Exception:
                log.warning('dcm4chee sync cycle failed', exc_info=True)
        time.sleep(interval)


def start_dcm4chee_sync():
    """Start the worker thread; no-op unless dicom_proxy=true."""
    if not dcm4chee_sync_enabled():
        log.info('dcm4chee self-heal sync disabled (dicom_proxy=false)')
        return None
    try:
        import asyncio
        main_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_loop = None
    thread = threading.Thread(target=_run_dcm4chee_sync, args=(main_loop,), daemon=True)
    thread.start()
    log.info('dcm4chee self-heal sync worker started (interval=%ss)',
             config.get('dcm4chee_sync_interval', '30'))
    return thread
