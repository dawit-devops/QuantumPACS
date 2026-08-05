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
            port=int(config.get('db_port', '5432')),
            min_size=2,
            max_size=pool_size,
            command_timeout=30,
            statement_cache_size=100,
        )

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    def acquire(self):
        if not self._pool:
            raise RuntimeError('Database pool not initialized — call setup() first')
        return self._pool.acquire(timeout=10)

    @property
    def pool(self):
        return self._pool
