"""Seed one test user per built-in role with a shared test password.

Idempotent: existing usernames are updated in place (password + role reset).
Usage: backend/venv/bin/python backend/seed_test_users.py [--allow-docker]

The docker guard (QUANTUMPACS_DOCKER) protects deployed runtimes from the
shared well-known test password. CI e2e runs set QUANTUMPACS_DOCKER for the
prod-like config branch, so the guard is overridable — explicitly, never by
default — via --allow-docker or QUANTUMPACS_SEED_ALLOW=1.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])

from config import is_docker
from db.database import Database
from db.roles import Roles
from db.users import hash_password

TEST_PASSWORD = 'Test@123456'
PREFIX = 'test.'


async def seed(allow_docker: bool = False):
    if is_docker() and not allow_docker:
        # These users share one well-known password — never in any deployed
        # runtime (docker stack is the prod-like smoke image). CI e2e opts in
        # explicitly with --allow-docker / QUANTUMPACS_SEED_ALLOW=1.
        print('Refusing to run in a docker/QUANTUMPACS_DOCKER environment. '
              'Pass --allow-docker (or set QUANTUMPACS_SEED_ALLOW=1) to '
              'override for test environments.', file=sys.stderr)
        sys.exit(1)

    db = Database()
    await db.setup(pool_size=4)
    created = updated = 0
    try:
        async with db.acquire() as conn:
            # Guard: users.tenant comes from migration 011; keep the script
            # runnable on sync-only databases.
            await conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant TEXT"
            )
            for role in await Roles(conn).get_all():
                slug = role['slug']
                username = f'{PREFIX}{slug}'
                ph = hash_password(TEST_PASSWORD)
                # Only test.tenant_admin is tenant-scoped (the seeded
                # `default` tenant); every other test user stays platform-side.
                tenant = 'default' if slug == 'tenant_admin' else None
                row = await conn.fetchrow(
                    "SELECT id FROM users WHERE username = $1", username,
                )
                await conn.execute(
                    """
                    INSERT INTO users (username, password, admin, status, role_id, tenant, created, updated)
                    VALUES ($1, $2, $3, 'active', $4, $5, now(), now())
                    ON CONFLICT (username) DO UPDATE SET
                        password = EXCLUDED.password,
                        role_id = EXCLUDED.role_id,
                        status = 'active',
                        tenant = EXCLUDED.tenant,
                        updated = now()
                    """,
                    username, ph, slug == 'super_admin', role['id'], tenant,
                )
                created += 1 if not row else 0
                updated += 1 if row else 0
                print(f'  {username:32s} -> {role["name"]}')
    finally:
        await db.close()
    print(f'\nSeeded {created} new, refreshed {updated} existing test users.')
    print(f'Login for all of them: username = test.<role>, password = {TEST_PASSWORD}')


def main():
    parser = argparse.ArgumentParser(
        description='Seed one test user per built-in role with a shared test password.',
    )
    parser.add_argument(
        '--allow-docker', action='store_true',
        help='override the QUANTUMPACS_DOCKER guard (CI e2e only)',
    )
    args = parser.parse_args()
    allow = args.allow_docker or os.getenv('QUANTUMPACS_SEED_ALLOW') == '1'
    asyncio.run(seed(allow_docker=allow))


if __name__ == '__main__':
    main()
