import json
import uuid

from pypika import Order
from pypika.functions import Count

from db.log import Log
from log import request_id_var


class AuditLog:
    def __init__(self, conn=None):
        self.conn = conn
        self.log_model = Log(conn)

    async def log_event(self, event_type, actor_id, resource_type, resource_id,
                        details=None, tenant=None, request_id=None):
        if request_id is None:
            request_id = request_id_var.get()
        trace_id = str(uuid.uuid4())

        payload = json.dumps({
            'event': event_type,
            'actor': actor_id,
            'resource': {'type': resource_type, 'id': resource_id},
            'detail': details,
            'tenant': tenant,
            'request_id': request_id,
        })

        q = self.log_model.insert().columns(
            'log', 'tenant', 'request_id', 'trace_id'
        ).insert(payload, tenant, request_id, trace_id)
        await self.conn.execute(str(q))

    async def query(self, tenant=None, event_type=None, actor_id=None, limit=50, offset=0):
        t = self.log_model.table
        q = self.log_model.select('*')

        if tenant is not None:
            q = q.where(t.tenant == tenant)
        if event_type is not None:
            q = q.where(t.log.like(f'%"event": "{event_type}"%'))
        if actor_id is not None:
            q = q.where(t.log.like(f'%"actor": {actor_id}%'))

        q = q.orderby(t.id, order=Order.desc).limit(limit).offset(offset)
        rows = await self.conn.fetch(str(q))
        return [dict(r) for r in rows]

    async def count(self, tenant=None, event_type=None, actor_id=None):
        t = self.log_model.table
        q = self.log_model.select(Count(1))

        if tenant is not None:
            q = q.where(t.tenant == tenant)
        if event_type is not None:
            q = q.where(t.log.like(f'%"event": "{event_type}"%'))
        if actor_id is not None:
            q = q.where(t.log.like(f'%"actor": {actor_id}%'))

        return await self.conn.fetchval(str(q))
