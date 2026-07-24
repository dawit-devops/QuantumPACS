from db.table import Table
from pypika import Order
from pypika.functions import Count


class Log(Table):
    name = 'logs'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
            log TEXT NOT NULL
        );
        """)

    async def add(self, text):
        q = self.insert().columns('log').insert(text)
        await self.exec(q)

    async def get_logs(self, offset=0, limit=10):
        q = self.select('*').orderby(
            self.table.id, order=Order.desc
        ).offset(offset).limit(limit)
        return await self.fetch(q)

    async def count_logs(self):
        q = self.select(Count(1))
        return await self.fetchval(q)
