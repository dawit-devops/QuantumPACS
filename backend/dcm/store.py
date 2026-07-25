import traceback
import uuid
from io import BytesIO

from db.conn import get_conn
from db.files import Files
from db.log import Log
from db.replica import Replica
from db.replica_files import ReplicaFiles
from dcm.file import get_meta
from log import get_logger
from storage.storage import Storage
from utils import hash_file

log = get_logger(__name__)


async def store_instance(ds, data):
    async with get_conn() as conn:
        try:
            ds = get_meta(ds)
            async with conn.transaction():
                master = await Replica(conn).master()

                hsh = hash_file(data)

                file_data = {
                    'name': str(uuid.uuid4()) + '.dcm',
                    'master': master['id'],
                    'hash': hsh,
                }
                file_data.update(ds)
                f = await Files(conn).insert_or_select(file_data)

                storage = await Storage.get(master)
                ret = await storage.copy(data, f)

                await ReplicaFiles(conn).add(
                    master['id'],
                    [{'id': f['id'], **ret}],
                )
        except Exception as e:
            log.error('DICOM store failed: %s', traceback.format_exc())
            await Log(conn).add(str(e))
            return False
    return True
