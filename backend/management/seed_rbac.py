"""Seed RBAC data (built-in roles + superadmin) for a fresh database.

Usage:
    python -m management.seed_rbac            # roles + superadmin
    python -m management.seed_rbac --roles-only

Mirrors the runtime lifecycle seed (backend/lifecycle.py sync_db block) so CI
and operators can provision roles/admin BEFORE uvicorn boots — app.py starts
with sync_db=False and therefore never creates the admin on its own. The
superadmin password comes from SUPERADMIN_PASS / config superadmin_pass.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.conn import get_conn, setup, teardown
from db.roles import Roles
from db.users import Users


async def seed(roles_only: bool = False):
    # The module runs standalone (python -m ...), so the pool must be
    # initialized before acquire() — lifecycle.setup normally does this at
    # app boot, which CI deliberately skips (sync_db=False).
    await setup(pool_size=2)
    try:
        async with get_conn() as conn:
            await Roles(conn).seed_built_in_roles()
            print('Seeded built-in roles', flush=True)
            if not roles_only:
                await Users(conn).add_superadmin()
                print('Superadmin ready (username=admin, password from SUPERADMIN_PASS)', flush=True)
    finally:
        await teardown()


def main():
    parser = argparse.ArgumentParser(
        description='Seed built-in RBAC roles and the superadmin user '
                    '(password from SUPERADMIN_PASS / config superadmin_pass).',
    )
    parser.add_argument(
        '--roles-only', action='store_true',
        help='seed the built-in roles but skip the superadmin user',
    )
    args = parser.parse_args()
    asyncio.run(seed(roles_only=args.roles_only))


if __name__ == '__main__':
    main()
