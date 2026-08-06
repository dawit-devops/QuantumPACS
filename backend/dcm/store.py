import json
import traceback
import uuid

from db.conn import get_conn
from db.files import Files
from db.log import Log
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.tenants import Tenants
from db.worklist import Worklist
from dcm.file import get_meta
from log import get_logger
from api.telemetry import dicom_cstore_throughput_bytes
from services.ingestion.routing import evaluate_routing_rules
from storage.storage import Storage
from utils import hash_file

log = get_logger(__name__)


async def _resolve_tenant(conn, tenant_id='', tenant_slug='', tenant_info=None):
    """Resolve the tenant scope for a non-HTTP ingestion path.

    HTTP paths (STOW-RS) pass request.state.*; the DICOM C-STORE SCP has no
    request, so it falls back to the seeded `default` tenant, whose data
    store IS the main database this path writes to.
    """
    try:
        if not tenant_info:
            slug = tenant_slug or 'default'
            info = await Tenants(conn).get_by_slug(slug) or {}
            if not info and slug != 'default':
                info = await Tenants(conn).get_by_slug('default') or {}
            tenant_slug = info.get('slug', '')
            tenant_info = info
            tenant_id = str(info.get('id', '')) if info else tenant_id
        elif not tenant_id:
            tenant_id = str(tenant_info.get('id', '')) if tenant_info.get('id') else tenant_id
    except Exception:
        log.warning('Tenant resolution failed; ingestion stays un-scoped', exc_info=True)
    return tenant_id, tenant_slug, tenant_info


async def match_worklist_in_progress(meta):
    """Transition a scheduled MWL entry to `in_progress` on first store.

    ME-05: a C-STORE proves the exam started, not that it completed — a
    partial study must not mark the entry performed. `performed` is
    reserved for the ORU^R01 results message (see hl7_server).
    """
    try:
        accession = meta.get('accession_number', '')
        study_uid = meta.get('study_instance_uid', '')
        if not accession or not study_uid:
            return
        async with get_conn() as conn:
            wl = Worklist(conn)
            existing = await wl.get_by_accession(accession)
            if existing and existing.get('status') == 'scheduled':
                await wl.mark_in_progress(accession, study_uid)
                log.info('Worklist entry %s marked in_progress', accession)
    except Exception:
        log.warning('Worklist match failed: %s', traceback.format_exc())


async def store_instance(ds, data, tenant_id='', tenant_slug='', tenant_info=None):
    async with get_conn() as conn:
        try:
            ds = get_meta(ds)
            hsh = hash_file(data)

            tenant_id, tenant_slug, tenant_info = await _resolve_tenant(
                conn, tenant_id, tenant_slug, tenant_info,
            )

            # Dedup by SOPInstanceUID (identity key), falling back to content
            # hash only for instances that carry no UID. Hash-only dedup
            # collapses distinct instances whose bytes are identical and
            # lets re-transmitted duplicates crash with a UniqueViolation.
            sop_uid = ds.get('sop_instance_uid', '')
            existing = None
            if sop_uid:
                existing = await Files(conn).get_by_sop_uid(sop_uid)
            if existing is None and not sop_uid:
                existing = await Files(conn).get_by_hash(hsh)
            if existing:
                log.info('Deduplicated: %s already stored as file %s', sop_uid or hsh, existing['id'])
                return True

            size = data.seek(0, 2)
            data.seek(0)

            # Quota applies to every ingestion path, not just HTTP uploads.
            quota_bytes = int((tenant_info or {}).get('storage_quota_bytes') or 0)
            if tenant_slug and quota_bytes > 0:
                used = await conn.fetchval('SELECT COALESCE(SUM(size), 0)::bigint FROM files') or 0
                if used + size > quota_bytes:
                    log.warning(
                        'Store rejected: tenant %s quota exceeded (%s + %s > %s)',
                        tenant_slug, used, size, quota_bytes,
                    )
                    return False

            async with conn.transaction():
                master = await Replica(conn).master()

                file_data = {
                    'name': str(uuid.uuid4()) + '.dcm',
                    'master': master['id'],
                    'hash': hsh,
                    'size': size,
                }
                file_data.update(ds)
                f = await Files(conn).insert_or_select(file_data)

            storage = await Storage.get(master)
            ret = await storage.copy(data, f)

            async with conn.transaction():
                await ReplicaFiles(conn).add(
                    master['id'],
                    [{'id': f['id'], **ret}],
                )

            if tenant_slug:
                await _persist_usage(conn, tenant_slug, size)

            await match_worklist_in_progress(ds)
            routes = await evaluate_routing_rules(ds, tenant_id=tenant_id)
            if routes:
                log.info(
                    'Study %s matched %d routing rule(s)',
                    ds.get('study_instance_uid', '?'), len(routes),
                )
            for route in routes:
                try:
                    dest_id = int(route['destination'])
                    dest_replica = await Replica(conn).get(dest_id)
                    if not dest_replica:
                        log.warning('Route %s: destination replica %s not found', route.get('rule_name'), dest_id)
                        continue
                    dest_storage = await Storage.get(dest_replica)
                    data.seek(0)
                    ret = await dest_storage.copy(data, f)
                    async with conn.transaction():
                        await ReplicaFiles(conn).add(dest_id, [{'id': f['id'], **ret}])
                    log.info('Routed file %s to replica %s', f['id'], dest_id)
                except Exception:
                    log.warning('Route %s failed: %s', route.get('rule_name', '?'), traceback.format_exc())
        except Exception as e:
            log.error('DICOM store failed: %s', traceback.format_exc())
            try:
                # logs.log is a JSON column (audit GIN index) — a bare text
                # message makes the INSERT itself fail.
                await Log(conn).add(json.dumps({'event': 'dicom.store_error', 'detail': str(e)}))
            except Exception:
                pass
            return False
    try:
        dicom_cstore_throughput_bytes.inc(size)
    except Exception:
        pass
    return True


async def _persist_usage(conn, tenant_slug, added_bytes):
    """Recompute and persist the tenant's storage usage after a store.

    Deliberately non-throwing: quota bookkeeping must never fail an ingest.
    """
    try:
        used = await conn.fetchval('SELECT COALESCE(SUM(size), 0)::bigint FROM files') or 0
        await Tenants(conn).persist_storage_used(tenant_slug, int(used))
    except Exception:
        log.warning('Storage usage persist failed for tenant %s', tenant_slug, exc_info=True)
