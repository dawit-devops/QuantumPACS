"""MPPS Consumer Service (S6-07).

Handles DICOM Modality Performed Procedure Step (MPPS) messages:
- N-CREATE: modality starts an exam → worklist entry → IN_PROGRESS
- N-SET:    modality completes/cancels an exam → worklist entry → COMPLETED/DISCONTINUED

The consumer also persists every event in ris_mpps_events (S6-08) for
audit and troubleshooting.
"""
from datetime import datetime, timezone

from db.conn import get_conn
from db.ris_mpps import RisMppsEvents
from log import get_logger

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
            now = datetime.now(timezone.utc)
            await conn.execute(
                "UPDATE worklist_entries SET status = 'in_progress', "
                "updated_at = $2, study_uid = $3 "
                "WHERE id = $1",
                worklist_row['id'], now, study_uid,
            )

            # Update exam status if one exists for this accession (S6-12)
            exam_row = await conn.fetchrow(
                "SELECT id, status FROM exams WHERE accession_number = $1",
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

            log.info('MPPS N-CREATE: accession %s → IN_PROGRESS', accession)

        return True

    async def handle_n_set(self, event) -> bool:
        """Handle N-SET: modality completes or cancels a procedure.

        Returns True if the worklist entry was updated, False otherwise.
        """
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

            # Update exam status if one exists for this accession (S6-12)
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

            log.info('MPPS N-SET: accession %s → %s', accession, wl_status)

        return True


def _extract_station_ae(event):
    """Extract calling AE title from the DICOM association."""
    assoc = getattr(event, 'assoc', None)
    requestor = getattr(assoc, 'requestor', None) if assoc else None
    return getattr(requestor, 'ae_title', '') or ''


def _extract_sps_status(ds):
    """Extract the ScheduledProcedureStepStatus from the dataset."""
    sps_seq = getattr(ds, 'ScheduledProcedureStepSequence', None)
    if sps_seq and len(sps_seq) > 0:
        return str(getattr(sps_seq[0], 'ScheduledProcedureStepStatus', '') or '')
    return ''


async def _record_event(conn, accession, event_type, mpps_status,
                        study_uid, station_ae, ds):
    """Persist an MPPS event to the audit trail."""
    import json
    from db.conn import get_tenant_slug
    now = datetime.now(timezone.utc)
    # Serialize a minimal representation of the DICOM dataset
    raw = {}
    try:
        raw = {str(k): str(v) for k, v in ds.items() if k.is_private is False}
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
