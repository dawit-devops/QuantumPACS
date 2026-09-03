"""Bridge DICOM ingest -> radiologist reading worklist (auto handoff).

Studies that land in the store outside the MWL -> technologist -> handoff
flow (zip uploads, single uploads, C-STORE without a worklist entry) are
invisible to the Reading Worklist: `reading_list()` only reads `exams`
rows with status='completed', and only the technologist-complete endpoint
created those. This module adds a per-instance ingest-time bridge that
creates the missing `exams` row and completes it once the study has
settled, so uploaded studies surface automatically in /reading.
"""
import asyncio
from datetime import datetime, timezone

from config import config
from db.conn import get_conn, get_database, get_tenant_slug
from db.tenants import TenantConnectionPool, uses_main_database, Tenants
from log import get_logger
from api.notify import notify_role
from db.audit_log import AuditLog

log = get_logger(__name__)

_settle_tasks: dict[str, asyncio.Task] = {}


def _handoff_enabled() -> bool:
    return str(config.get('auto_reading_handoff', 'true')).lower() in ('1', 'true', 'yes', 'on')


def _settle_seconds() -> int:
    try:
        return max(0, int(config.get('auto_handoff_settle_seconds', '60')))
    except (TypeError, ValueError):
        return 60


def _effective_accession(meta: dict) -> str:
    accession = (meta.get('accession_number') or '').strip()
    if accession:
        return accession
    study_uid = meta.get('study_instance_uid', '') or ''
    return f'AUTO-{study_uid.replace(".", "")[:12]}' if study_uid else ''


async def _worklist_owns(conn, accession: str, tenant: str) -> bool:
    if not accession:
        return False
    row = await conn.fetchrow(
        "SELECT id FROM worklist_entries WHERE accession_number = $1 LIMIT 1",
        accession,
    )
    return row is not None


async def _ensure_exam(conn, meta: dict, tenant: str) -> tuple[str | None, bool]:
    accession = _effective_accession(meta)
    mrn = (meta.get('patient_id', '') or '').strip()
    study_uid = meta.get('study_instance_uid', '') or ''
    if not accession or not mrn or not study_uid:
        return None, False

    raw_acc = (meta.get('accession_number') or '').strip()
    if not raw_acc:
        try:
            await conn.execute(
                "UPDATE studies SET accession_number = $2 "
                "WHERE study_instance_uid = $1 AND (accession_number = '' OR accession_number IS NULL)",
                study_uid, accession,
            )
        except Exception:
            log.warning("Failed to backfill study accession for %s", study_uid, exc_info=True)

    exam_id = await conn.fetchval(
        """INSERT INTO exams
           (patient_id, patient_name, patient_birth_date, patient_sex,
            accession_number, requested_procedure_desc, modality,
            priority, status, tenant_id, created_by, created_at, updated_at)
         SELECT $1, $2, $3, $4, $5, $6, $7, 'routine', 'ready',
                $8, '', now(), now()
         WHERE NOT EXISTS (
           SELECT 1 FROM exams
           WHERE tenant_id = $8 AND accession_number = $5 AND patient_id = $1
         )
         RETURNING id""",
        mrn,
        meta.get('patient_name', ''),
        meta.get('patient_birth_date', ''),
        meta.get('patient_sex', ''),
        accession,
        meta.get('study_description', ''),
        meta.get('modality', ''),
        tenant,
    )
    if exam_id:
        return str(exam_id), True
    row = await conn.fetchrow(
        "SELECT id FROM exams WHERE tenant_id = $1 AND accession_number = $2 AND patient_id = $3",
        tenant, accession, mrn,
    )
    return (str(row['id']), False) if row else (None, False)


async def _maybe_complete(conn, exam_id: str, study_uid: str, settle: int, now) -> bool:
    row = await conn.fetchrow(
        """SELECT received_instances, expected_instances, study_status, updated_at
           FROM studies WHERE study_instance_uid = $1""",
        study_uid,
    )
    if not row:
        return False
    complete = False
    if row['study_status'] == 'complete' and (row['received_instances'] or 0) > 0:
        complete = True
    elif row['updated_at'] and (now - row['updated_at']).total_seconds() >= settle:
        complete = True
    if not complete:
        return False
    result = await conn.execute(
        "UPDATE exams SET status = 'completed', completed_at = $2, updated_at = $2 "
        "WHERE id = $1 AND status = 'ready'",
        exam_id, now,
    )
    if result != 'UPDATE 0':
        log.info("Exam %s completed (study %s settled)", exam_id, study_uid)
    return result != 'UPDATE 0'


async def _delayed_settle(study_uid: str, exam_id: str, tenant_slug: str):
    settle = _settle_seconds()
    await asyncio.sleep(settle)
    try:
        now = datetime.now(timezone.utc)
        if not tenant_slug:
            async with get_conn() as conn:
                await _maybe_complete(conn, exam_id, study_uid, settle, now)
            return
        async with get_database().acquire() as reg_conn:
            info = await Tenants(reg_conn).get_by_slug(tenant_slug)
        if not info:
            return
        if uses_main_database(info):
            async with get_conn() as conn:
                await _maybe_complete(conn, exam_id, study_uid, settle, now)
        else:
            pool = await TenantConnectionPool.get(tenant_slug, info)
            async with pool.acquire() as conn:
                await _maybe_complete(conn, exam_id, study_uid, settle, now)
            TenantConnectionPool.release(tenant_slug)
    except asyncio.CancelledError:
        raise
    except Exception:
        log.warning("Delayed settle check failed for study %s exam %s", study_uid, exam_id, exc_info=True)
    finally:
        _settle_tasks.pop(study_uid, None)


def _schedule_settle(study_uid: str, exam_id: str, tenant_slug: str):
    if not study_uid or not exam_id:
        return
    existing = _settle_tasks.get(study_uid)
    if existing and not existing.done():
        existing.cancel()
    task = asyncio.create_task(
        _delayed_settle(study_uid, exam_id, tenant_slug),
    )
    _settle_tasks[study_uid] = task


async def ensure_reading_exam(conn, meta: dict, tenant_slug: str = '', source: str = ''):
    """Ensure a radiologist-reading exam exists for a newly stored study.

    Idempotent per (tenant_id, accession_number, patient_id). Called once
    per stored instance; subsequent instances for the same study find the
    existing exam and re-evaluate completion (last instance wins).

    Args:
        conn: Tenant-scoped asyncpg connection.
        meta: get_meta() output dict from the DICOM instance.
        tenant_slug: Tenant slug.
        source: 'dicom', 'zip', or 'upload' — for logging.

    Returns:
        exam_id (str) or None when skipped.
    """
    if not _handoff_enabled():
        return None

    log.debug("ensure_reading_exam called for study %s patient %s source %s",
              meta.get('study_instance_uid', ''), meta.get('patient_id', ''), source)

    study_uid = (meta.get('study_instance_uid', '') or '').strip()
    mrn = (meta.get('patient_id', '') or '').strip()
    if not study_uid or not mrn:
        return None

    accession = _effective_accession(meta)
    if not accession:
        return None

    tenant = get_tenant_slug() or tenant_slug or 'default'

    try:
        await conn.execute(
            "UPDATE studies SET updated_at = now() WHERE study_instance_uid = $1",
            study_uid,
        )
    except Exception:
        log.warning("Failed to bump updated_at for study %s", study_uid, exc_info=True)

    if await _worklist_owns(conn, accession, tenant):
        return None

    exam_id, created = await _ensure_exam(conn, meta, tenant)
    if not exam_id:
        return None

    if created:
        try:
            await notify_role(
                conn, 'radiologist', 'study.arrived',
                f'Study arrived: {accession}',
                f'{meta.get("patient_name", "")} — {meta.get("modality", "")} ready for review',
                f'/reading/{exam_id}',
            )
        except Exception:
            log.warning("Notification failed for exam %s", exam_id, exc_info=True)
        try:
            await AuditLog(conn).log_event(
                event_type='exam.auto_created',
                actor_id='system',
                resource_type='exam',
                resource_id=exam_id,
                details={
                    'accession_number': accession,
                    'modality': meta.get('modality', ''),
                    'source': source,
                    'study_instance_uid': study_uid,
                },
                tenant=tenant,
            )
        except Exception:
            log.warning("Audit log failed for exam %s", exam_id, exc_info=True)

    settle = _settle_seconds()
    now = datetime.now(timezone.utc)
    flipped = await _maybe_complete(conn, exam_id, study_uid, settle, now)

    if not flipped:
        _schedule_settle(study_uid, exam_id, tenant_slug)

    return exam_id