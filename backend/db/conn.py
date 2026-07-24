"""Database connection management — unified singleton pool.
Use get_conn() or get_database().acquire() interchangeably; both return from the same pool."""
import asyncpg

from config import config
from db.database import Database

database = Database()


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
    except Exception:
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
    except Exception:
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
    return database.acquire()


def get_database():
    return database


async def teardown():
    await database.close()
