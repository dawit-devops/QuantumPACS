import asyncio
import sys

from es import es
import db.conn
from db.users import Users
from db.table import Table
from log import get_logger
from api.redis_client import get_client as get_redis

log = get_logger(__name__)

_RETRYABLE = (ConnectionError, OSError, asyncio.TimeoutError)


async def setup(db_pool_size=None, sync_db=False):
    success = False
    last_exc = None
    for i in range(30):
        try:
            await db.conn.setup(pool_size=db_pool_size)
            await es.setup()
            success = True
            break
        except _RETRYABLE as e:
            log.warning('Startup attempt %d/30 failed: %s', i + 1, e)
            last_exc = e
            try:
                await teardown()
            except Exception:
                pass
        except Exception as e:
            log.critical('Non-retryable startup error: %s', e)
            await teardown()
            sys.exit(1)
        await asyncio.sleep(1)

    if not success:
        log.critical("Can't connect to database or elasticsearch: %s", last_exc)
        await teardown()
        sys.exit(1)

    log.info('Connected to database')
    await get_redis()

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
    from api.redis_client import close_client as close_redis
    await close_redis()
    log.info('Shutdown complete')
