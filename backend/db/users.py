import binascii
import hashlib
import hmac
import os
import random
import string
from datetime import datetime, timezone

from config import config
from exceptions import ApiException
from db.table import Table
from pypika import Table as Table_
from pypika.functions import Count


def rand_pswd(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def hash_password(pswd, salt=None):
    if salt is None:
        salt = os.urandom(16)
    data = hashlib.pbkdf2_hmac('sha256', pswd.encode('utf8'), salt, 600000)
    return binascii.hexlify(salt + data).decode('utf8')


class Users(Table):
    name = 'users'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username CITEXT NOT NULL,
            password TEXT NOT NULL,
            admin BOOLEAN NOT NULL DEFAULT FALSE,
            status TEXT NOT NULL DEFAULT 'active',
            needs_rehash BOOLEAN NOT NULL DEFAULT FALSE,
            created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
            updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc')
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS users_username on users(username);
        """)

    @staticmethod
    def to_json(data):
        return dict(data)

    @staticmethod
    def _verify_password(password, stored):
        raw = binascii.unhexlify(stored)
        if len(raw) == 32:
            data = hashlib.pbkdf2_hmac('sha256', password.encode('utf8'), b'', 10000)
            return binascii.hexlify(data).decode('utf8') == stored
        salt = raw[:16]
        expected = hash_password(password, salt)
        return hmac.compare_digest(expected, stored)

    async def login(self, username, password):
        q = self.select('*').where(self.table.username == username)
        data = await self.fetchone(q)
        if not data:
            raise ApiException('User does not exists')
        if not self._verify_password(password, data['password']):
            raise ApiException('Password is not correct')
        if data['status'] != 'active':
            raise ApiException('User deactivated')

        raw = binascii.unhexlify(data['password'])
        if len(raw) == 32:
            ph = hash_password(password)
            q = self.update().where(self.table.id == data['id']).set(self.table.password, ph)
            await self.exec(q)
        elif data.get('needs_rehash'):
            ph = hash_password(password)
            q = self.update().where(self.table.id == data['id']).set(self.table.password, ph)
            await self.exec(q)

        return data

    async def add_superadmin(self):
        async with self.conn.transaction():
            q = self.select('*').where(self.table.username == 'admin')
            data = await self.fetchone(q)
            if not data:
                pswd = hash_password(config['superadmin_pass'])
                from db.roles import Roles
                role = await Roles(self.conn).get_by_slug('super_admin')
                role_id = role['id'] if role else None
                q = self.insert().columns('username', 'password', 'admin', 'role_id').insert(
                    'admin', pswd, True, role_id,
                )
                await self.exec(q)

    async def get_user_role(self, user_id):
        from db.roles import Roles
        q = self.select('role_id').where(self.table.id == user_id)
        row = await self.fetchone(q)
        if not row or not row['role_id']:
            return None, []
        role = await Roles(self.conn).get(row['role_id'])
        if role:
            perms = role.get('permissions') or []
            if isinstance(perms, str):
                import json
                perms = json.loads(perms)
            return role['slug'], perms
        return None, []

    async def update_last_login(self, user_id):
        now = datetime.now(timezone.utc)
        q = self.update().where(self.table.id == user_id).set(self.table.last_login, now)
        await self.exec(q)

    async def change_password(self, user, new_password, current_password):
        q = self.select('password').where(self.table.id == user.id)
        row = await self.fetchone(q)
        if not row:
            raise ApiException('User not found')
        if not self._verify_password(current_password, row['password']):
            raise ApiException('Current password is incorrect')
        pswd = hash_password(new_password)
        q = self.update().where(self.table.id == user.id).set(self.table.password, pswd)
        await self.exec(q)

    async def add_user(self, username, is_admin, role_id=None):
        q = self.insert().columns('username', 'password', 'admin', 'role_id').insert(username, '', is_admin, role_id).returning('id')
        user_id = await self.fetchval(q)
        pswd = rand_pswd()
        ph = hash_password(pswd)
        q = self.update().where(self.table.id == user_id).set(self.table.password, ph)
        await self.exec(q)
        return {'password': pswd}

    async def get_users(self, offset=None, limit=None, username=None):
        if offset is None:
            offset = 0
        if limit is None:
            limit = 20
        roles_t = Table_('roles')
        q = self.select(
            'id', 'username', 'admin', 'created', 'status',
            roles_t.id.as_('role_id'),
            roles_t.name.as_('role_name'),
            roles_t.slug.as_('role_slug'),
        ).left_join(roles_t).on(self.table.role_id == roles_t.id)
        if username:
            q = q.where(self.table.username.ilike('%' + username + '%'))
        q = q.orderby('username').offset(offset).limit(limit)
        return await self.fetch(q)

    async def count_users(self, username=None):
        q = self.select(Count(1))
        if username:
            q = q.where(self.table.username.ilike('%' + username + '%'))
        return await self.fetchval(q)

    async def deactivate(self, user_id):
        q = self.update().where(self.table.id == user_id).set(self.table.status, 'deactivated')
        await self.exec(q)
        await self.increment_token_version(user_id)

    async def new_pswd(self, user_id):
        exists = await self.fetchval(self.select(self.table.id).where(self.table.id == user_id))
        if not exists:
            raise RuntimeError(f'User {user_id} not found')
        pswd = rand_pswd()
        ph = hash_password(pswd)
        q = self.update().where(self.table.id == user_id).set(self.table.password, ph)
        await self.exec(q)
        return pswd

    async def update_role(self, user_id, role_id):
        q = self.update().where(self.table.id == user_id).set(self.table.role_id, role_id)
        await self.exec(q)
        await self.increment_token_version(user_id)

    async def increment_token_version(self, user_id):
        q = self.update().where(self.table.id == user_id).set(
            self.table.token_version, self.table.token_version + 1,
        )
        await self.exec(q)

    async def get_token_version(self, user_id):
        q = self.select('token_version').where(self.table.id == user_id)
        return await self.fetchval(q) or 0

    async def bulk_increment_token_version_by_role(self, role_id):
        q = self.update().where(self.table.role_id == role_id).set(
            self.table.token_version, self.table.token_version + 1,
        )
        await self.exec(q)

    async def is_active(self, user_id):
        q = self.select('status').where(self.table.id == user_id)
        status = await self.fetchval(q)
        return status == 'active'

    async def get_auth_state(self, user_id):
        q = self.select('status', 'token_version').where(self.table.id == user_id)
        row = await self.fetchone(q)
        if not row:
            return False, 0
        return row['status'] == 'active', row.get('token_version') or 0
