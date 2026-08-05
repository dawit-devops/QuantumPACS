"""Seed one test user per built-in role with a shared test password.

Idempotent: existing usernames are updated in place (password + role reset).
Usage: backend/venv/bin/python backend/seed_test_users.py
"""
import asyncio
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])

from db.database import Database
from db.roles import Roles
from db.users import hash_password

TEST_PASSWORD = 'Test@123456'
PREFIX = 'test.'


async def main():
    db = Database()
    await db.setup(pool_size=4)
    created = updated = 0
    try:
        async with db.acquire() as conn:
            for role in await Roles(conn).get_all():
                slug = role['slug']
                username = f'{PREFIX}{slug}'
                ph = hash_password(TEST_PASSWORD)
                row = await conn.fetchrow(
                    "SELECT id FROM users WHERE username = $1", username,
                )
                await conn.execute(
                    """
                    INSERT INTO users (username, password, admin, status, role_id, created, updated)
                    VALUES ($1, $2, $3, 'active', $4, now(), now())
                    ON CONFLICT (username) DO UPDATE SET
                        password = EXCLUDED.password,
                        role_id = EXCLUDED.role_id,
                        status = 'active',
                        updated = now()
                    """,
                    username, ph, slug == 'super_admin', role['id'],
                )
                created += 1 if not row else 0
                updated += 1 if row else 0
                print(f'  {username:32s} -> {role["name"]}')
    finally:
        await db.close()
    print(f'\nSeeded {created} new, refreshed {updated} existing test users.')
    print(f'Login for all of them: username = test.<role>, password = {TEST_PASSWORD}')


asyncio.run(main())
