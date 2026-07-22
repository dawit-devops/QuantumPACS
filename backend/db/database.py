"""PostgreSQL async connection pool wrapper.
Usage: get_database().acquire() for connections, setup() at startup, close() at shutdown."""
import asyncpg

from config import config


class Database:
    def __init__(self):
        self._pool = None

    async def setup(self, pool_size=None):
        pool_size = pool_size or 8
        self._pool = await asyncpg.create_pool(
            user=config['db_user'],
            password=config['db_password'],
            database=config['db_database'],
            host=config['db_host'],
            port=5432,
            max_size=pool_size,
            min_size=pool_size,
        )

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    def acquire(self):
        return self._pool.acquire() if self._pool else None

    @property
    def pool(self):
        return self._pool
