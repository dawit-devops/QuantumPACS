import json
import traceback
import uuid
from contextlib import asynccontextmanager

from config import config
from db import conn as db_conn
from db.conn import get_conn, get_database
from db.files import Files
from db.log import Log
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.tenants import Tenants, TenantConnectionPool, uses_main_database
from db.worklist import Worklist
from dcm.file import get_meta
from log import get_logger
from api.telemetry import dicom_cstore_throughput_bytes
from services.ingestion.routing import evaluate_routing_rules
from storage.storage import Storage
from utils import hash_file

log = get_logger(__name__)


class TenantResolutionError(Exception):
    """A tenant scope that must be resolved could not be (ME-05).

    Raised when an explicit tenant reference — an AE-mapped slug or an
    explicitly passed non-default slug — has no registry entry. Silently
    falling back to the default/main store would persist a tenant's study
    in the wrong database, so the store fails loudly instead.
    """


def resolve_tenant_slug_for_ae(ae_title):
    """Map a calling AE title to a tenant slug (CR-02).

    Reads the `dicom_ae_tenant_map` config — comma-separated `AE:slug` pairs,
    matched case-insensitively. An empty map, an unmatched AE, or no AE title
    yields '' (the caller then falls back to the seeded `default` tenant,
    whose data store is the main database).
    """
    raw = (config.get('dicom_ae_tenant_map', '') or '').strip()
    if not raw or not ae_title:
        return ''
    for pair in raw.split(','):
        pair = pair.strip()
        if ':' not in pair:
            continue
        ae, slug = pair.split(':', 1)
        if ae.strip().upper() == ae_title.upper():
            return slug.strip()
    return ''


@asynccontextmanager
async def tenant_db_scope(tenant_slug='', tenant_info=None):
    """Scope get_conn() to a tenant's pool for the duration of the block.

    CR-02: the DICOM SCP runs outside the HTTP middleware that sets the
    per-request tenant scope (C-STORE/C-FIND handlers have no Request
    object), so the DICOM handlers must set it themselves. This manager
    takes a pool lease, switches the db.conn ContextVar, and restores the
    previous scope + releases the lease on exit. When the tenant's data
    store IS the main database (default tenant) — or no tenant is given —
    the block runs un-scoped on the main pool.
    """
    if not tenant_slug or uses_main_database(tenant_info or {}):
        yield
        return
    pool = await TenantConnectionPool.get(tenant_slug, tenant_info)
    previous = db_conn.get_request_tenant()
    previous_slug = db_conn.get_tenant_slug()
    db_conn.set_request_tenant(pool.acquire)
    # CR-01: out-of-request indexers (Files.add's direct ES hook) read this
    # ContextVar to tag documents with the tenant that owns the rows.
    db_conn.set_tenant_slug(tenant_slug)
    try:
        yield
    finally:
        if previous is not None:
            db_conn.set_request_tenant(previous)
        else:
            db_conn.reset_request_tenant()
        db_conn.set_tenant_slug(previous_slug)
        TenantConnectionPool.release(tenant_slug)


async def _resolve_tenant(conn, tenant_id='', tenant_slug='', tenant_info=None, required=False):
    """Resolve the tenant scope for a non-HTTP ingestion path.

    HTTP paths (STOW-RS) pass request.state.*; the DICOM C-STORE SCP has no
    request, so it falls back to the seeded `default` tenant, whose data
    store IS the main database this path writes to.

    ME-05: an explicit (non-default) slug — from the AE map or the caller —
    is a hard requirement, so resolution failures raise
    TenantResolutionError instead of silently writing to the main store.
    Implicit/unmapped scopes keep the graceful fallback.
    """
    try:
        if not tenant_info:
            slug = tenant_slug or 'default'
            info = await Tenants(conn).get_by_slug(slug) or {}
            if not info and slug != 'default':
                info = await Tenants(conn).get_by_slug('default') or {}
            if required and not info:
                raise TenantResolutionError(f'Tenant {slug!r} not found in registry')
            tenant_slug = info.get('slug', '')
            tenant_info = info
            tenant_id = str(info.get('id', '')) if info else tenant_id
        elif not tenant_id:
            tenant_id = str(tenant_info.get('id', '')) if tenant_info.get('id') else tenant_id
    except TenantResolutionError:
        raise
    except Exception:
        log.warning('Tenant resolution failed; ingestion stays un-scoped', exc_info=True)
    return tenant_id, tenant_slug, tenant_info


async def match_worklist_in_progress(meta, tenant_slug=''):
    """Transition a scheduled MWL entry to `in_progress` on first store.

    ME-05: a C-STORE proves the exam started, not that it completed — a
    partial study must not mark the entry performed. `performed` is
    reserved for the ORU^R01 results message (see hl7_server).

    The MWL match runs inside the tenant's DB scope (store_instance opens a
    tenant_db_scope before calling this), so get_conn() below already
    resolves to the owning tenant's worklist_entries table. tenant_slug is
    threaded through explicitly (G-4) as defense-in-depth documentation of
    which tenant the accession belongs to.
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


def _next_study_status(received, expected, current):
    """Study status after `received` instances are on disk (ME-05).

    Status only moves forward: receiving -> complete/incomplete. A study is
    complete when an expected count is known and reached; once complete it
    stays complete (retransmits/dedup must not regress it).
    """
    if current == 'complete':
        return 'complete'
    if expected > 0:
        return 'complete' if received >= expected else 'incomplete'
    return 'receiving'


async def _bump_study_counts(conn, meta):
    """Count a newly stored instance against its study (ME-05, ME-01).

    Single atomic UPDATE: the old read-then-write let concurrent stores of
    the same study both read the pre-increment count and under-count (lost
    update). RETURNING is a no-op when no study row exists yet.
    Deliberately non-throwing: completeness bookkeeping must never fail an
    ingest (same contract as `_persist_usage`).
    """
    try:
        study_uid = meta.get('study_instance_uid', '')
        if not study_uid:
            return
        row = await conn.fetchrow(
            """
            UPDATE studies
               SET received_instances = received_instances + 1,
                   study_status = CASE
                     WHEN study_status = 'complete' THEN 'complete'
                     WHEN expected_instances > 0
                       AND received_instances + 1 >= expected_instances THEN 'complete'
                     WHEN expected_instances > 0 THEN 'incomplete'
                     ELSE 'receiving'
                   END
             WHERE study_instance_uid = $1
             RETURNING received_instances, study_status
            """,
            study_uid,
        )
        if row:
            log.debug(
                'Study %s now %s (%s instances)',
                study_uid, row['study_status'], row['received_instances'],
            )
    except Exception:
        log.warning('Study count bump failed: %s', traceback.format_exc())


async def store_instance(ds, data, tenant_id='', tenant_slug='', tenant_info=None, ae_title=''):
    """Persist a DICOM instance (C-STORE / STOW-RS).

    CR-02: when the calling AE maps to a non-default tenant
    (dicom_ae_tenant_map), the instance lands in that tenant's database —
    its own patients/studies/series/files tables — via the tenant pool.
    Control-plane reads (tenant registry, replica registry, routing rules)
    stay on the main database; tenant DBs run the same migrations but their
    replicas/routing tables are empty by design.
    """
    if not tenant_slug:
        tenant_slug = resolve_tenant_slug_for_ae(ae_title)

    size = 0
    try:
        async with get_database().acquire() as registry_conn:
            tenant_id, tenant_slug, tenant_info = await _resolve_tenant(
                registry_conn, tenant_id, tenant_slug, tenant_info,
                required=bool(tenant_slug) and tenant_slug != 'default',
            )

        async with tenant_db_scope(tenant_slug, tenant_info):
            async with get_conn() as conn:
                ds = get_meta(ds)
                hsh = hash_file(data)

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
                    # HI-2: read the running counter from the tenants registry
                    # (maintained on store/delete) instead of a full-table
                    # SUM(files.size) scan on every C-STORE — O(1) vs O(n).
                    used = max(0, int((tenant_info or {}).get('storage_used_bytes') or 0))
                    if used + size > quota_bytes:
                        log.warning(
                            'Store rejected: tenant %s quota exceeded (%s + %s > %s)',
                            tenant_slug, used, size, quota_bytes,
                        )
                        return False

                # Replica registry lives in the main DB — a tenant DB's
                # replicas table is empty, so `master()` must not run there.
                async with get_database().acquire() as control_conn:
                    master = await Replica(control_conn).master()

                async with conn.transaction():
                    file_data = {
                        'name': str(uuid.uuid4()) + '.dcm',
                        'master': master['id'],
                        'hash': hsh,
                        'size': size,
                    }
                    file_data.update(ds)
                    # HI-2: rows land in the tenant's files table — tag them
                    # with the owning slug so the files.tenant guard and the
                    # ES indexer can scope by it ('' → platform/main store).
                    file_data['tenant'] = tenant_slug or None
                    f = await Files(conn).insert_or_select(file_data)

                storage = await Storage.get(master)
                ret = await storage.copy(data, f)

                async with get_database().acquire() as control_conn:
                    async with conn.transaction():
                        await ReplicaFiles(control_conn).add(
                            master['id'],
                            [{'id': f['id'], **ret}],
                        )

                if tenant_slug:
                    # HI-2: increment the running counter by this instance's
                    # size rather than recomputing SUM(files.size).
                    await _persist_usage(tenant_slug, size)

                await match_worklist_in_progress(ds, tenant_slug=tenant_slug)
                await _bump_study_counts(conn, ds)
        # tenant scope ended — routing rules live in the main DB and must be
        # read from it, so routing evaluation happens outside the scope.
        routes = await evaluate_routing_rules(ds, tenant_id=tenant_id)
        if routes:
            log.info(
                'Study %s matched %d routing rule(s)',
                ds.get('study_instance_uid', '?'), len(routes),
            )
        for route in routes:
            try:
                dest_id = int(route['destination'])
                async with get_database().acquire() as control_conn:
                    dest_replica = await Replica(control_conn).get(dest_id)
                if not dest_replica:
                    log.warning('Route %s: destination replica %s not found', route.get('rule_name'), dest_id)
                    continue
                dest_storage = await Storage.get(dest_replica)
                data.seek(0)
                ret = await dest_storage.copy(data, f)
                async with get_database().acquire() as control_conn:
                    async with control_conn.transaction():
                        await ReplicaFiles(control_conn).add(dest_id, [{'id': f['id'], **ret}])
                log.info('Routed file %s to replica %s', f['id'], dest_id)
            except Exception:
                log.warning('Route %s failed: %s', route.get('rule_name', '?'), traceback.format_exc())
    except TenantResolutionError:
        # ME-05: fail loudly rather than persist a tenant's study in the
        # wrong (main) store.
        log.error('Store rejected: %s', traceback.format_exc())
        return False
    except Exception as e:
        log.error('DICOM store failed: %s', traceback.format_exc())
        try:
            # Audit rows are read by the API from the main DB (the multi-tenant
            # logs table), so the error record always lands there.
            async with get_database().acquire() as audit_conn:
                await Log(audit_conn).add(json.dumps({'event': 'dicom.store_error', 'detail': str(e)}))
        except Exception:
            pass
        return False
    try:
        dicom_cstore_throughput_bytes.inc(size)
    except Exception:
        pass
    return True


async def _persist_usage(tenant_slug, delta_bytes):
    """Adjust the tenant's running storage counter after a store.

    DELTA_BYTES is this instance's size (+); the registry `tenants.storage_used_bytes`
    column is the authoritative counter (incremented here, decremented on
    delete), replacing the former per-instance `SUM(files.size)` full-table
    scan. Updates the tenants registry row in the main database, never a tenant
    data store. Deliberately non-throwing: quota bookkeeping must never fail
    an ingest.
    """
    try:
        async with get_database().acquire() as conn:
            await Tenants(conn).adjust_storage_used(tenant_slug, int(delta_bytes))
    except Exception:
        log.warning('Storage usage adjust failed for tenant %s', tenant_slug, exc_info=True)
