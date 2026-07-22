"""Database connection management — legacy per-process pool + new Database singleton.
Prefer get_database() for new code; get_conn() maintains backward compatibility."""
import os

import asyncpg

from config import config
from db.database import Database

db = {}
database = Database()


async def init_db():
    conn = await asyncpg.connect(
        user='postgres',
        password=config['db_password'],
        database='postgres',
        host=config['db_host'],
        port=5432,
    )
    try:
        await conn.execute('CREATE DATABASE openpacs')
    except:
        pass
    await conn.close()

    conn = await asyncpg.connect(
        user='postgres',
        password=config['db_password'],
        database='openpacs',
        host=config['db_host'],
        port=5432,
    )
    try:
        await conn.execute('CREATE EXTENSION intarray')
        await conn.execute('CREATE EXTENSION citext')
    except:
        pass
    await conn.close()


async def setup(pool_size=None):
    global db
    pool_size = pool_size or 8
    pool = await asyncpg.create_pool(
        user=config['db_user'],
        password=config['db_password'],
        database=config['db_database'],
        host=config['db_host'],
        port=5432,
        max_size=pool_size,
        min_size=pool_size,
    )
    db[os.getpid()] = pool

    await database.setup(pool_size)


async def create_conn():
    return await asyncpg.connect(
        user=config['db_user'],
        password=config['db_password'],
        database=config['db_database'],
        host=config['db_host'],
        port=5432,
    )


def get_conn():
    return db[os.getpid()].acquire()


def get_database():
    return database


async def teardown():
    pid = os.getpid()
    await db[pid].close()
    del db[pid]

    await database.close()
