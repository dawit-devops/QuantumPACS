"""Tenant migration runner — runs alembic migrations on all tenant databases.
Usage:
    python -m management.tenant_migrate              # migrate all tenants
    python -m management.tenant_migrate <slug>       # migrate specific tenant
"""
import asyncio
import os
import sys

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


async def _get_tenants(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT slug, db_name, db_host, db_port, db_user, db_password "
            "FROM tenants WHERE status = 'active' ORDER BY slug"
        )
        return [dict(r) for r in rows]


async def _migrate_one(tenant):
    slug = tenant['slug']
    print(f'Migrating tenant: {slug} (db={tenant["db_name"]})', flush=True)
    env = os.environ.copy()
    env['TENANT_SLUG'] = slug
    proc = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'alembic', 'upgrade', 'head',
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        print(f'  FAILED: {slug}', flush=True)
        print(stdout.decode() if stdout else '', flush=True)
        return False
    print('  OK', flush=True)
    return True


async def main():
    target_slug = sys.argv[1] if len(sys.argv) > 1 else None

    pool = await asyncpg.create_pool(
        user=config['db_user'],
        password=config['db_password'],
        database=config['db_database'],
        host=config['db_host'],
        port=int(config.get('db_port', '5432')),
        min_size=1,
        max_size=2,
    )

    try:
        tenants = await _get_tenants(pool)
        if not tenants:
            print('No active tenants found')
            return

        if target_slug:
            tenants = [t for t in tenants if t['slug'] == target_slug]
            if not tenants:
                print(f'Tenant not found: {target_slug}')
                sys.exit(1)

        results = await asyncio.gather(*[_migrate_one(t) for t in tenants], return_exceptions=True)
        failed = sum(1 for r in results if r is False)
        total = len(tenants)

        print(f'\n{total - failed}/{total} tenants migrated successfully')
        if failed:
            print(f'{failed} tenant(s) failed')
            sys.exit(1)
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
