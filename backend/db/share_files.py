from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from pypika import Order

from db.table import Table
from log import get_logger
from utils import rand_str

log = get_logger(__name__)


class SharedFiles(Table):
    name = 'shared_files'

    async def sync_db(self):
        await self.exec("""    
        CREATE TABLE IF NOT EXISTS shared_files (
            id SERIAL PRIMARY KEY,
            created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
            expires TIMESTAMP NOT NULL,
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            hash TEXT NOT NULL
        );
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS shared_files_hash ON shared_files(hash);
        """)

    async def share(self, file_id, duration):
        key = rand_str()
        expires = datetime.now(timezone.utc) + relativedelta(hours=duration)
        q = self.insert().columns(
            'file_id', 'hash', 'expires'
        ).insert(
            file_id, key, expires,
        )
        await self.exec(q)
        return key

    async def check(self, key):
        q = self.select('*').where(self.table.hash == key)
        sf = await self.fetchone(q)
        now = datetime.now(timezone.utc)
        if not sf:
            return None

        if sf['expires'] < now:
            q = self.query().where(self.table.id == sf['id']).delete()
            await self.exec(q)
            return None
        return sf['file_id']

    async def cleanup_expired(self):
        q = self.query().where(self.table.expires < datetime.now(timezone.utc)).delete()
        cnt = await self.exec(q)
        if cnt:
            log.info('Cleaned up %s expired shared files', cnt)

    async def list_for_file(self, file_id):
        q = self.select('id', 'created', 'expires', 'hash').where(
            self.table.file_id == file_id
        ).orderby(self.table.created, order=Order.desc)
        return await self.fetch(q)

    async def revoke(self, share_id, file_id):
        q = self.query().where(
            (self.table.id == share_id) & (self.table.file_id == file_id)
        ).delete()
        return await self.exec(q)
