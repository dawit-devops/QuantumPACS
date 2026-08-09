"""user_tenant_grants — opt-in cross-tenant clinical access rights (R2-03).

A row (user_id, tenant_slug) lets a clinical user read workload in another
tenant — but only when their role also carries the CROSS_TENANT_READ
permission (defense in depth: grant row AND permission must both be present).
The table lives in the main database; grants are global, not per-tenant.
"""
from pypika import functions as fn
from pypika.dialects import PostgreSQLQuery as Query_

from db.table import Table


def _coerce_user_id(user_id):
    # JWT claims carry the SERIAL users.id as int, but some callers pass the
    # string form; asyncpg would otherwise error comparing int4 = text.
    if isinstance(user_id, str) and user_id.isdigit():
        return int(user_id)
    return user_id


class UserTenantGrants(Table):
    name = 'user_tenant_grants'

    async def sync_db(self):
        pass

    async def has(self, user_id, tenant_slug):
        # select('1') would render as SELECT "1" (pypika quotes bare strings
        # as columns); Count(1) is an actual literal and avoids the 500.
        # (count or 0): COUNT never yields NULL, but a stub/driver fetchval
        # may — treat that as "no grant", never as a TypeError.
        q = self.select(fn.Count(1)).where(
            (self.table.user_id == _coerce_user_id(user_id))
            & (self.table.tenant_slug == tenant_slug)
        )
        return (await self.fetchval(q) or 0) > 0

    async def scope_for(self, user_id, tenant_slug):
        """The grant scope ('read' or 'write') for a user+tenant pair, or
        None when no grant row exists. Mutating endpoints must demand
        'write'; 'read' unlocks cross-tenant visibility only (R5-HI-1)."""
        q = self.select(self.table.scope).where(
            (self.table.user_id == _coerce_user_id(user_id))
            & (self.table.tenant_slug == tenant_slug)
        )
        return await self.fetchval(q)

    async def scope_for(self, user_id, tenant_slug):
        """The grant scope ('read' or 'write') for a user+tenant pair, or
        None when no grant row exists. Mutating endpoints must demand
        'write'; 'read' unlocks cross-tenant visibility only (R5-HI-1)."""
        q = self.select(self.table.scope).where(
            (self.table.user_id == _coerce_user_id(user_id))
            & (self.table.tenant_slug == tenant_slug)
        )
        return await self.fetchval(q)

    async def list_for_user(self, user_id):
        q = self.select(
            self.table.tenant_slug, self.table.scope, self.table.created_at,
        ).where(self.table.user_id == _coerce_user_id(user_id))
        data = await self.fetch(q)
        return [dict(row) for row in data]

    async def list_for_tenant(self, tenant_slug):
        q = self.select(
            self.table.user_id,
            self.table.created_by,
            self.table.created_at,
        ).where(self.table.tenant_slug == tenant_slug)
        data = await self.fetch(q)
        return [dict(row) for row in data]

    async def add(self, user_id, tenant_slug, scope='read', created_by=None):
        q = self.insert().columns(
            self.table.user_id, self.table.tenant_slug, self.table.scope,
            self.table.created_by,
        ).insert(
            _coerce_user_id(user_id), tenant_slug, scope, created_by or '',
        ).on_conflict(self.table.user_id, self.table.tenant_slug).do_nothing()
        return await self.exec(q)

    async def remove(self, user_id, tenant_slug):
        q = Query_.from_(self.table).delete().where(
            (self.table.user_id == _coerce_user_id(user_id))
            & (self.table.tenant_slug == tenant_slug)
        )
        return await self.exec(q)