"""Database connection management — unified singleton pool.
Use get_conn() or get_database().acquire() interchangeably; both return from the same pool.

Tenant routing: TenantMiddleware sets the request-scoped tenant contextvar
(set_request_tenant) to the resolved tenant pool's acquire callable; get_conn()
then yields tenant-DB connections without any handler changes. The ContextVar
keeps concurrent requests isolated (each request task sees only its own tenant).
"""
import contextvars

import asyncpg

from config import config
from db.database import Database

database = Database()

# Callable returning an async context manager for the CURRENT request's tenant
# pool (asyncpg Pool.acquire or Database.acquire for the default tenant, whose
# data store is the main database). None → main pool.
_request_tenant_pool: contextvars.ContextVar = contextvars.ContextVar(
    'request_tenant_pool', default=None,
)


def set_request_tenant(pool_acquire):
    """Scope get_conn() to the given tenant pool for the current request."""
    _request_tenant_pool.set(pool_acquire)


def reset_request_tenant():
    """Clear the request tenant scope (must run in a finally)."""
    _request_tenant_pool.set(None)


def get_request_tenant():
    """Current request's tenant pool acquire callable, or None (main pool)."""
    return _request_tenant_pool.get()


async def init_db():
    conn = await asyncpg.connect(
        user='postgres',
        password=config['db_password'],
        database='postgres',
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )
    try:
        await conn.execute('CREATE DATABASE quantumpacs')
    except asyncpg.DuplicateDatabaseError:
        pass
    await conn.close()

    conn = await asyncpg.connect(
        user='postgres',
        password=config['db_password'],
        database='quantumpacs',
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )
    try:
        await conn.execute('CREATE EXTENSION intarray')
        await conn.execute('CREATE EXTENSION citext')
    except asyncpg.DuplicateObjectError:
        pass
    await conn.close()


async def setup(pool_size=None):
    pool_size = pool_size or int(config.get('db_pool_size', '8'))
    await database.setup(pool_size)


async def create_conn():
    return await asyncpg.connect(
        user=config['db_user'],
        password=config['db_password'],
        database=config['db_database'],
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
    )


def get_conn():
    acquire = _request_tenant_pool.get()
    if acquire is not None:
        try:
            return acquire(timeout=10)
        except TypeError:
            # Database.acquire() takes no timeout kwarg — used when the
            # resolved tenant's data store IS the main database (default tenant).
            return acquire()
    return database.acquire()


def get_database():
    return database


async def teardown():
    await database.close()
