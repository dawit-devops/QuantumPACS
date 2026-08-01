"""Seed one user per built-in role for RBAC end-to-end testing.

Creates users named role_<slug> (role_admin, role_technologist, ...) each
linked to its role so login tokens carry the role's permissions.

DEV/CI ONLY: uses a shared, fixed password by default (SEED_RBAC_PASSWORD).
Idempotent — re-running resets passwords and re-links role_id.

Usage: python -m management.seed_rbac
"""

import asyncio
import os

from api.permissions import BUILT_IN_ROLES
from db.conn import get_conn
from db.roles import Roles
from db.users import Users, hash_password
import lifecycle

SKIP_ROLES = {'super_admin', 'tenant_admin'}


async def main():
    password = os.getenv('SEED_RBAC_PASSWORD', 'pa55w0rd')
    await lifecycle.setup(sync_db=True)
    print('=== Seeding RBAC role users ===')
    try:
        async with get_conn() as conn:
            roles = Roles(conn)
            users = Users(conn)
            for slug in BUILT_IN_ROLES:
                if slug in SKIP_ROLES:
                    continue
                role = await roles.get_by_slug(slug)
                if not role:
                    print(f'  skipping {slug}: role row missing (run migrations + seed_built_in_roles)')
                    continue
                username = f'role_{slug}'
                ph = hash_password(password)
                q = users.select('*').where(users.table.username == username)
                data = await users.fetchone(q)
                if not data:
                    q = users.insert().columns(
                        'username', 'password', 'admin', 'role_id',
                    ).insert(username, ph, False, role['id']).returning('id')
                    await users.fetchval(q)
                    print(f'  created  {username} -> {slug}')
                else:
                    q = users.update().where(users.table.id == data['id']).set(
                        users.table.role_id, role['id'],
                    ).set(users.table.password, ph)
                    await users.exec(q)
                    print(f'  updated  {username} -> {slug}')
    finally:
        await lifecycle.teardown()
    print('=== done ===')


if __name__ == '__main__':
    asyncio.run(main())
