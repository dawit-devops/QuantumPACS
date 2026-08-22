"""MPPS Consumer Service (S6-07).

Handles DICOM Modality Performed Procedure Step (MPPS) messages:
- N-CREATE: modality starts an exam → worklist entry → IN_PROGRESS
- N-SET:    modality completes/cancels an exam → worklist entry → COMPLETED/DISCONTINUED

The consumer also persists every event in ris_mpps_events (S6-08) for
audit and troubleshooting.
"""
from datetime import datetime, timezone
import time

from api.telemetry import ris_mpps_latency_seconds
from db.audit_log import AuditLog
from db.conn import get_conn, get_tenant_slug
from log import get_logger
from services.pacs_echo.service import echo_to_pacs

log = get_logger(__name__)

# Valid MPPS status values and their worklist/exam mappings
MPPS_TO_WORKLIST_STATUS = {
    'IN_PROGRESS': 'in_progress',
    'COMPLETED': 'performed',
    'DISCONTINUED': 'cancelled',
}


class MppsConsumer:
    """Processes DICOM MPPS N-CREATE and N-SET messages."""

    async def handle_n_create(self, event) -> bool:
        """Handle N-CREATE: modality starts performing a procedure.

        Returns True if the worklist entry was updated, False otherwise.
        """
        started = time.monotonic()
        ds = event.identifier
        accession = str(getattr(ds, 'AccessionNumber', '') or '')
        if not accession:
            log.warning('MPPS N-CREATE: no AccessionNumber in dataset')
            return False

        study_uid = str(getattr(ds, 'StudyInstanceUID', '') or '')
        station_ae = _extract_station_ae(event)
        mpps_status = _extract_sps_status(ds) or 'IN_PROGRESS'

        async with get_conn() as conn:
            # Find the worklist entry by accession
            worklist_row = await conn.fetchrow(
                "SELECT id, accession_number, status FROM worklist_entries "
                "WHERE accession_number = $1",
                accession,
            )
            if not worklist_row:
                log.warning('MPPS N-CREATE: no worklist entry for accession %s',
                            accession)
                return False

            # Update worklist status to in_progress
            # M-3: a terminal entry must not regress — a late or repeated
            # N-CREATE (modality retry, duplicate association) must not
            # un-complete a performed or cancelled exam. The message is
            # still recorded for audit.
            terminal = worklist_row['status'] in ('performed', 'cancelled')

            # M-2: the multi-write sequence (worklist + exam + event +
            # audit) must be atomic — a mid-sequence failure must not
            # leave half-applied state.
            async with conn.transaction():
                if not terminal:
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        "UPDATE worklist_entries SET status = 'in_progress', "
                        "updated_at = $2, study_uid = $3 "
                        "WHERE id = $1",
                        worklist_row['id'], now, study_uid,
                    )

                    # Update exam status if one exists for this accession
                    # (S6-12)
                    exam_row = await conn.fetchrow(
                        "SELECT id, status FROM exams "
                        "WHERE accession_number = $1",
                        accession,
                    )
                    if exam_row:
                        await conn.execute(
                            "UPDATE exams SET status = 'in_progress', "
                            "updated_at = $2 WHERE id = $1",
                            exam_row['id'], now,
                        )

                # Persist the MPPS event for audit
                await _record_event(conn, accession, 'N_CREATE', mpps_status,
                                    study_uid, station_ae, ds)

                # H7: MPPS transitions must land in audit_log (resource_type
                # 'worklist_entry') so the S6-16 tracking timeline shows the
                # modality-reported progress, not just internal status
                # changes.
                await AuditLog(conn).log_event(
                    'MPPS_N_CREATE', 'system', 'worklist_entry',
                    worklist_row['id'],
                    details={'accession': accession,
                             'mpps_status': mpps_status,
                             'study_uid': study_uid,
                             'station_ae': station_ae})

            log.info('MPPS N-CREATE: accession %s → IN_PROGRESS', accession)

        # S6-11 / RIS-SL-22: MPPS → tracking latency histogram.
        ris_mpps_latency_seconds.labels(
            event_type='N_CREATE',
            facility=get_tenant_slug() or 'default').observe(
            time.monotonic() - started)
        return True

    async def handle_n_set(self, event) -> bool:
        """Handle N-SET: modality completes or cancels a procedure.

        Returns True if the worklist entry was updated, False otherwise.
        """
        started = time.monotonic()
        ds = event.identifier
        accession = str(getattr(ds, 'AccessionNumber', '') or '')
        if not accession:
            log.warning('MPPS N-SET: no AccessionNumber in dataset')
            return False

        study_uid = str(getattr(ds, 'StudyInstanceUID', '') or '')
        station_ae = _extract_station_ae(event)
        mpps_status = _extract_sps_status(ds) or 'COMPLETED'

        # Map MPPS status to worklist status
        wl_status = MPPS_TO_WORKLIST_STATUS.get(mpps_status, 'performed')

        async with get_conn() as conn:
            worklist_row = await conn.fetchrow(
                "SELECT id, accession_number, status FROM worklist_entries "
                "WHERE accession_number = $1",
                accession,
            )
            if not worklist_row:
                log.warning('MPPS N-SET: no worklist entry for accession %s',
                            accession)
                return False

            # M-2: the multi-write sequence (worklist + exam + event +
            # audit) must be atomic.
            async with conn.transaction():
                now = datetime.now(timezone.utc)
                if wl_status == 'performed':
                    await conn.execute(
                        "UPDATE worklist_entries SET status = 'performed', "
                        "performed_at = $2, updated_at = $3, study_uid = $4 "
                        "WHERE id = $1",
                        worklist_row['id'], now, now, study_uid,
                    )
                elif wl_status == 'cancelled':
                    await conn.execute(
                        "UPDATE worklist_entries SET status = 'cancelled', "
                        "updated_at = $2 "
                        "WHERE id = $1",
                        worklist_row['id'], now,
                    )
                else:
                    await conn.execute(
                        "UPDATE worklist_entries SET status = $2, "
                        "updated_at = $3 WHERE id = $1",
                        worklist_row['id'], wl_status, now,
                    )

                # Update exam status if one exists for this accession
                # (S6-12)
                exam_row = await conn.fetchrow(
                    "SELECT id, status FROM exams WHERE accession_number = $1",
                    accession,
                )
                if exam_row:
                    if wl_status == 'performed':
                        await conn.execute(
                            "UPDATE exams SET status = 'completed', "
                            "updated_at = $2 WHERE id = $1",
                            exam_row['id'], now,
                        )
                    elif wl_status == 'cancelled':
                        await conn.execute(
                            "UPDATE exams SET status = 'cancelled', "
                            "updated_at = $2 WHERE id = $1",
                            exam_row['id'], now,
                        )

                # Persist the MPPS event for audit
                await _record_event(conn, accession, 'N_SET', mpps_status,
                                    study_uid, station_ae, ds)

                # H7: MPPS transitions must land in audit_log (resource_type
                # 'worklist_entry') so the S6-16 tracking timeline shows the
                # modality-reported progress, not just internal status
                # changes.
                await AuditLog(conn).log_event(
                    'MPPS_N_SET', 'system', 'worklist_entry',
                    worklist_row['id'],
                    details={'accession': accession,
                             'mpps_status': mpps_status,
                             'study_uid': study_uid,
                             'station_ae': station_ae})

            log.info('MPPS N-SET: accession %s → %s', accession, wl_status)

        # H8 / S6-09: a completed exam probes PACS connectivity. Fired
        # outside the connection block so a slow echo never holds a pooled
        # connection; the stub is best-effort and never raises.
        if wl_status == 'performed':
            await echo_to_pacs()

        # S6-11 / RIS-SL-22: MPPS → tracking latency histogram.
        ris_mpps_latency_seconds.labels(
            event_type='N_SET',
            facility=get_tenant_slug() or 'default').observe(
            time.monotonic() - started)
        return True


def _extract_station_ae(event):
    """Extract calling AE title from the DICOM association."""
    assoc = getattr(event, 'assoc', None)
    requestor = getattr(assoc, 'requestor', None) if assoc else None
    return getattr(requestor, 'ae_title', '') or ''


def _extract_sps_status(ds):
    """Extract the MPPS status from the dataset.

    CR-2: the status of a performed step lives in (0040,0252)
    PerformedProcedureStepStatus inside the performed-step block
    (0040,0270) Scheduled Step Attributes Sequence. The original
    implementation read ScheduledProcedureStepStatus from the SPS
    sequence — which modalities echo as IN_PROGRESS — so COMPLETED
    N-SET messages never mapped to `performed`. Read by tag because
    pydicom stores (0040,0270) under its retired keyword
    ScheduledStepAttributesSequence, which varies by version. Fall back
    to the SPS element only for legacy/non-conformant datasets that
    lack a performed-step block.
    """
    pps = ds.get_item((0x0040, 0x0270)) if hasattr(ds, 'get_item') else None
    if pps is not None and getattr(pps, 'VR', None) == 'SQ' and pps.value:
        status = str(getattr(pps.value[0], 'PerformedProcedureStepStatus', '') or '')
        if status:
            return status
    sps_seq = getattr(ds, 'ScheduledProcedureStepSequence', None)
    if sps_seq and len(sps_seq) > 0:
        return str(getattr(sps_seq[0], 'ScheduledProcedureStepStatus', '') or '')
    return ''


async def _record_event(conn, accession, event_type, mpps_status,
                        study_uid, station_ae, ds):
    """Persist an MPPS event to the audit trail."""
    import json
    now = datetime.now(timezone.utc)
    # Serialize a minimal representation of the DICOM dataset
    # Conformance: key by keyword ('AccessionNumber'), not tag string
    # ('(0008,0050)'), so audit rows are inspectable/greppable.
    raw = {}
    try:
        raw = {elem.keyword or str(elem.tag): str(elem.value)
               for elem in ds if not elem.tag.is_private}
    except Exception:
        raw = {'error': 'failed to serialize dataset'}
    await conn.execute(
        "INSERT INTO ris_mpps_events "
        "(accession_number, event_type, mpps_status, study_uid, "
        " station_ae_title, raw_message, tenant_id, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)",
        accession, event_type, mpps_status, study_uid,
        station_ae, json.dumps(raw),
        get_tenant_slug() or 'default', now,
    )
