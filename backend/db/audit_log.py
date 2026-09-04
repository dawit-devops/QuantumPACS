import json
import uuid

from datetime import date, datetime
from log import request_id_var

from db.conn import get_tenant_slug


def _uuid_safe(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


class AuditLog:
    def __init__(self, conn=None):
        self.conn = conn

    async def log_event(self, event_type, actor_id, resource_type, resource_id,
                        details=None, tenant=None, request_id=None):
        # M-6: tag every audit row with the effective tenant scope. The
        # TenantMiddleware sets the request-scoped slug ContextVar per request;
        # if a caller doesn't pass an explicit tenant (and most don't), fall
        # back to it so tenant-scoped actions are attributable across the
        # shared `logs` table instead of landing with a NULL tenant.
        if tenant is None:
            tenant = get_tenant_slug()
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
        }, default=_uuid_safe)

        await self.conn.execute(
            'INSERT INTO logs (log, tenant, request_id, trace_id) VALUES ($1, $2, $3, $4)',
            payload, tenant, request_id, trace_id,
        )

    @staticmethod
    def _extract(row):
        d = dict(row)
        try:
            payload = json.loads(d['log']) if isinstance(d.get('log'), str) else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        resource = payload.get('resource', {})
        if isinstance(resource, str):
            try:
                resource = json.loads(resource)
            except (json.JSONDecodeError, TypeError):
                resource = {}
        detail = payload.get('detail', {})
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except (json.JSONDecodeError, TypeError):
                detail = {}
        return {
            'id': d['id'],
            'created_at': str(d.get('created', '')) if d.get('created') else None,
            'event_type': d.get('event_type') or payload.get('event'),
            'actor': d.get('actor_name') or payload.get('actor', 'system'),
            'resource_type': resource.get('type') if isinstance(resource, dict) else None,
            'resource_id': resource.get('id') if isinstance(resource, dict) else None,
            'description': detail.get('description') if isinstance(detail, dict) else (detail if isinstance(detail, str) else None),
            'tenant': d.get('tenant') or payload.get('tenant'),
            'payload': payload,
        }

    async def query(self, event_type=None, actor=None, actor_id=None, date_from=None, date_to=None,
                    tenant=None, cursor=None, limit=50, offset=None, resource_id=None):
        where = ["l.log LIKE '{%'"]
        params = []
        idx = 1

        if event_type:
            if isinstance(event_type, str):
                event_type = [event_type]
            clauses = []
            for et in event_type:
                clauses.append(f"(l.log::json->>'event') = ${idx}")
                params.append(et)
                idx += 1
            where.append(f"({' OR '.join(clauses)})")
        if actor:
            where.append(f"u.username ILIKE ${idx} || '%'")
            params.append(actor)
            idx += 1
        if actor_id is not None:
            where.append(f"(l.log::json->>'actor') = ${idx}")
            params.append(str(actor_id))
            idx += 1
        if date_from:
            where.append(f"l.created >= ${idx}")
            params.append(date_from)
            idx += 1
        if date_to:
            where.append(f"l.created <= ${idx}::date + interval '1 day' - interval '1 second'")
            params.append(date_to)
            idx += 1
        if tenant:
            where.append(f"l.tenant = ${idx}")
            params.append(tenant)
            idx += 1
        if cursor:
            where.append(f"l.id < ${idx}")
            params.append(int(cursor))
            idx += 1
        if resource_id:
            where.append(f"(l.log::json->'resource'->>'id') = ${idx}")
            params.append(str(resource_id))
            idx += 1

        q = f"""
            SELECT l.id, l.created, l.log, l.tenant,
                   u.username AS actor_name,
                   (l.log::json->>'event') AS event_type
            FROM logs l
            LEFT JOIN users u ON u.id::text = (l.log::json->>'actor')
            WHERE {' AND '.join(where)}
            ORDER BY l.id DESC
            LIMIT ${idx}
        """
        params.append(limit)
        if offset:
            q += f" OFFSET ${idx + 1}"
            params.append(int(offset))
        rows = await self.conn.fetch(q, *params)
        return [self._extract(r) for r in rows]

    async def count(self, event_type=None, actor=None, actor_id=None, date_from=None, date_to=None, tenant=None):
        where = ["l.log LIKE '{%'"]
        params = []
        idx = 1

        if event_type:
            if isinstance(event_type, str):
                event_type = [event_type]
            clauses = []
            for et in event_type:
                clauses.append(f"(l.log::json->>'event') = ${idx}")
                params.append(et)
                idx += 1
            where.append(f"({' OR '.join(clauses)})")
        if actor:
            where.append(f"u.username ILIKE ${idx} || '%'")
            params.append(actor)
            idx += 1
        if actor_id is not None:
            where.append(f"(l.log::json->>'actor') = ${idx}")
            params.append(str(actor_id))
            idx += 1
        if date_from:
            where.append(f"l.created >= ${idx}")
            params.append(date_from)
            idx += 1
        if date_to:
            where.append(f"l.created <= ${idx}::date + interval '1 day' - interval '1 second'")
            params.append(date_to)
            idx += 1
        if tenant:
            where.append(f"l.tenant = ${idx}")
            params.append(tenant)
            idx += 1

        q = f"""
            SELECT COUNT(1)
            FROM logs l
            LEFT JOIN users u ON u.id::text = (l.log::json->>'actor')
            WHERE {' AND '.join(where)}
        """
        return await self.conn.fetchval(q, *params)

    async def get_event_types(self):
        rows = await self.conn.fetch("""
            SELECT DISTINCT (l.log::json->>'event') AS event_type
            FROM logs l
            WHERE l.log LIKE '{%'
              AND (l.log::json->>'event') IS NOT NULL
            ORDER BY event_type
        """)
        return [r['event_type'] for r in rows]

    async def get_actors(self, search=None, limit=20):
        params = [limit]
        idx = 2
        where = ["l.log LIKE '{%'", "u.username IS NOT NULL"]
        if search:
            where.append(f"u.username ILIKE ${idx} || '%'")
            params.append(search)
            idx += 1

        q = f"""
            SELECT DISTINCT u.username
            FROM logs l
            JOIN users u ON u.id::text = (l.log::json->>'actor')
            WHERE {' AND '.join(where)}
            LIMIT $1
        """
        rows = await self.conn.fetch(q, *params)
        return [r['username'] for r in rows if r['username']]
