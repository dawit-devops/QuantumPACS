import asyncio
import sys

from es import es
import db.conn
from db.users import Users
from db.table import Table
from log import get_logger

log = get_logger(__name__)


async def setup(db_pool_size=None, sync_db=False):
    success = False
    for i in range(30):
        try:
            await db.conn.setup(pool_size=db_pool_size)
            await es.setup()
            success = True
            break
        except Exception as e:
            log.warning('Startup attempt %d/30 failed: %s', i + 1, e)
            try:
                await teardown()
            except Exception:
                pass
        await asyncio.sleep(1)

    if not success:
        log.critical("Can't connect to database or elasticsearch")
        sys.exit(1)

    log.info('Connected to database')

    if sync_db:
        async with db.conn.get_conn() as conn:
            for t in Table.tables:
                try:
                    await t(conn).sync_db()
                except Exception:
                    log.error('Table sync failed: %s', t.name)
                    raise

            await Users(conn).add_superadmin()
            log.info('Database schema synced')


async def teardown():
    await db.conn.teardown()
    await es.teardown()
    log.info('Shutdown complete')
