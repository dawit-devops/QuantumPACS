import hashlib
import secrets

from db.table import Table


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _prefix_from_key(key: str) -> str:
    return key[4:12]


class ApiKeys(Table):
    name = 'api_keys'

    async def sync_db(self):
        pass

    @staticmethod
    def to_json(data):
        d = dict(data)
        d.pop('key_hash', None)
        d['created_at'] = str(d.get('created_at', ''))
        if d.get('expires_at'):
            d['expires_at'] = str(d['expires_at'])
        if d.get('last_used_at'):
            d['last_used_at'] = str(d['last_used_at'])
        if d.get('permissions') and isinstance(d['permissions'], (list, str)):
            import json
            if isinstance(d['permissions'], str):
                d['permissions'] = json.loads(d['permissions'])
        return d

    @staticmethod
    def generate(service_name: str, created_by=None, expires_in_days=None):
        raw_token = secrets.token_urlsafe(32)
        raw_key = f'qpk_{raw_token}'
        key_hash = _hash_key(raw_key)
        prefix = _prefix_from_key(raw_key)
        return {
            'raw_key': raw_key,
            'key_hash': key_hash,
            'prefix': prefix,
        }

    async def store(self, name: str, key_hash: str, prefix: str,
                    service_name: str, permissions=None,
                    created_by=None, expires_at=None):
        if permissions is None:
            permissions = []
        import json
        perms_json = json.dumps(permissions)
        q = self.insert().columns(
            self.table.name, self.table.key_hash, self.table.prefix,
            self.table.service_name, self.table.permissions,
            self.table.created_by, self.table.expires_at,
        ).insert(
            name, key_hash, prefix, service_name, perms_json,
            created_by, expires_at,
        ).returning(self.table.id)
        return await self.fetchval(q)

    async def validate(self, key: str):
        prefix = _prefix_from_key(key)
        q = self.select('*').where(self.table.prefix == prefix)
        row = await self.fetchone(q)
        if not row:
            return None
        if not row['enabled']:
            return None
        if row['expires_at'] and row['expires_at'] < __import__('datetime').datetime.now(
                tz=__import__('datetime').timezone.utc):
            return None
        if row['key_hash'] != _hash_key(key):
            return None
        await self.exec(
            self.update()
            .where(self.table.id == row['id'])
            .set(self.table.last_used_at, 'NOW()')
        )
        return self.to_json(row)

    async def get_all(self):
        q = self.select('*').orderby(self.table.created_at)
        rows = await self.fetch(q)
        return [self.to_json(r) for r in rows]

    async def get(self, key_id):
        q = self.select('*').where(self.table.id == key_id)
        row = await self.fetchone(q)
        return self.to_json(row) if row else None

    async def revoke(self, key_id):
        q = self.update().where(self.table.id == key_id).set(self.table.enabled, False)
        await self.exec(q)
