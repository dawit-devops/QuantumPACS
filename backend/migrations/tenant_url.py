"""Resolve tenant database URL from registry for tenant-aware migrations."""
import asyncio
import os

import asyncpg

from config import config as app_config

_tenant_slug = os.environ.get('TENANT_SLUG')


async def async_get_tenant_url(slug=None):
    target = slug or _tenant_slug
    if not target:
        return None

    c = await asyncpg.connect(
        user=app_config['db_user'],
        password=app_config['db_password'],
        database=app_config['db_database'],
        host=app_config['db_host'],
        port=int(app_config.get('db_port', '5432')),
    )
    try:
        row = await c.fetchrow(
            "SELECT db_name, db_host, db_port, db_user, db_password "
            "FROM tenants WHERE slug = $1", target
        )
        info = dict(row) if row else None
    finally:
        await c.close()

    if not info:
        raise RuntimeError(f'Tenant not found in registry: {target}')

    user = info.get('db_user', app_config['db_user'])
    password = info.get('db_password', app_config['db_password'])
    host = info.get('db_host', app_config['db_host'])
    port = info.get('db_port', int(app_config.get('db_port', '5432')))
    db = info['db_name']
    from sqlalchemy.engine import URL
    return URL.create(
        'postgresql+asyncpg',
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=db,
    ).render_as_string(hide_password=False)


def get_tenant_url(slug=None):
    return asyncio.run(async_get_tenant_url(slug=slug))
