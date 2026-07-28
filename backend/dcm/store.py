import traceback
import uuid
from io import BytesIO

from db.conn import get_conn
from db.files import Files
from db.log import Log
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.worklist import Worklist
from dcm.file import get_meta
from log import get_logger
from api.telemetry import dicom_cstore_throughput_bytes
from services.ingestion.routing import evaluate_routing_rules
from storage.storage import Storage
from utils import hash_file

log = get_logger(__name__)


async def match_worklist_performed(meta):
    try:
        accession = meta.get('accession_number', '')
        study_uid = meta.get('study_instance_uid', '')
        if not accession or not study_uid:
            return
        async with get_conn() as conn:
            wl = Worklist(conn)
            existing = await wl.get_by_accession(accession)
            if existing and existing.get('status') == 'scheduled':
                await wl.mark_performed(accession, study_uid)
                log.info('Worklist entry %s auto-marked performed', accession)
    except Exception:
        log.warning('Worklist match failed: %s', traceback.format_exc())


async def store_instance(ds, data):
    async with get_conn() as conn:
        try:
            ds = get_meta(ds)
            hsh = hash_file(data)

            existing = await Files(conn).get_by_hash(hsh)
            if existing:
                log.info('Deduplicated: hash %s already stored as file %s', hsh, existing['id'])
                return True

            async with conn.transaction():
                master = await Replica(conn).master()

                file_data = {
                    'name': str(uuid.uuid4()) + '.dcm',
                    'master': master['id'],
                    'hash': hsh,
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
        except Exception as e:
            log.error('DICOM store failed: %s', traceback.format_exc())
            await Log(conn).add(str(e))
            return False
    await match_worklist_performed(ds)
    routes = await evaluate_routing_rules(ds)
    if routes:
        log.info('Study %s matched %d routing rule(s)', ds.get('study_instance_uid', '?'), len(routes))
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
    try:
        data.seek(0, 2)
        dicom_cstore_throughput_bytes.inc(data.tell())
    except Exception:
        pass
    return True
