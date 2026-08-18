"""RIS interface engine persistence (E-RIS-02) — exception queue + endpoints.

The engine (services/hl7_engine/service.py) persists every inbound HL7
message to ris_hl7_messages with a status lifecycle
(RECEIVED→PARSED→PROCESSED / FAILED) so nothing is dropped silently;
list_failed() powers retry_failed(). Tenant scope follows the spec's
facility_id→tenant_id adaptation documented in migrations 066/067.
"""

from datetime import date, datetime, time, timezone
import json

from pypika import Order
from pypika.functions import Count

from db.conn import get_tenant_slug
from db.table import Table


def _json_dumps(value):
    """Serialize JSONB values for storage. parse_hl7_message() yields
    datetime.date (patient_dob) which json.dumps rejects — converting to
    ISO strings keeps the audit row writable (best-effort persist)."""
    def _clean(obj):
        if isinstance(obj, (date, datetime, time)):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, (list, tuple)):
            return [_clean(v) for v in obj]
        return obj
    return json.dumps(_clean(value))


class RisHl7Messages(Table):
    name = 'ris_hl7_messages'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_hl7_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            endpoint_id UUID REFERENCES ris_interface_endpoints(id),
            message_type TEXT NOT NULL,
            trigger_event TEXT NOT NULL,
            control_id TEXT NOT NULL DEFAULT '',
            raw_message TEXT NOT NULL,
            parsed_segments JSONB,
            status TEXT NOT NULL DEFAULT 'RECEIVED'
                CHECK (status IN ('RECEIVED', 'PARSED', 'PROCESSED', 'FAILED',
                                  'RETRYING', 'ACKNOWLEDGED', 'QUEUED')),
            error_message TEXT,
            retry_count INT DEFAULT 0,
            max_retries INT DEFAULT 3,
            processed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_hl7_tenant_status
            ON ris_hl7_messages (tenant_id, status, created_at)
        """)
        await self.exec("CREATE INDEX IF NOT EXISTS ix_ris_hl7_control ON ris_hl7_messages (control_id)")
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_hl7_type ON ris_hl7_messages (message_type, trigger_event)
        """)

    async def create(self, data):
        # Raw SQL with $n params + ::jsonb cast: Table's pypika builder cannot
        # carry params and inlining a dict raises (see roles.py for the same
        # pattern). Without the cast asyncpg treats the JSON text as a JSON
        # *string*, double-encoding it.
        return await self.conn.fetchval(
            'INSERT INTO ris_hl7_messages '
            '(tenant_id, endpoint_id, message_type, trigger_event, control_id, '
            ' raw_message, parsed_segments, status, error_message, retry_count, max_retries) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11) RETURNING id',
            get_tenant_slug() or 'default',
            data.get('endpoint_id'),
            data['message_type'],
            data['trigger_event'],
            data.get('control_id', ''),
            data['raw_message'],
            _json_dumps(data['parsed_segments']) if data.get('parsed_segments') else None,
            data.get('status', 'RECEIVED'),
            data.get('error_message'),
            0,
            data.get('max_retries', 3),
        )

    async def update_status(self, msg_id, status, error='', retry_count=None, processed_at=None):
        q = self.update().set(self.table.status, status)
        if error:
            q = q.set(self.table.error_message, error)
        if retry_count is not None:
            q = q.set(self.table.retry_count, retry_count)
        q = q.set(
            self.table.processed_at,
            processed_at if processed_at is not None else datetime.now(timezone.utc),
        ).where(self.table.id == msg_id)
        await self.exec(q)

    async def list_failed(self, limit=50, max_retries=3):
        """Exception queue: FAILED messages still below their retry budget."""
        q = self.select(
            'id', 'retry_count', 'raw_message', 'error_message', 'created_at',
        ).where(
            (self.table.status == 'FAILED') & (self.table.retry_count < max_retries),
        ).orderby(self.table.created_at).limit(limit)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def get(self, msg_id):
        q = self.select('*').where(self.table.id == msg_id)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def list_by_endpoint(self, endpoint_id, limit=50, offset=0):
        """Message history for one interface endpoint (S3-15 dashboard)."""
        q = self.select(
            'id', 'message_type', 'trigger_event', 'control_id', 'status',
            'error_message', 'retry_count', 'created_at', 'processed_at',
        ).where(self.table.endpoint_id == endpoint_id).orderby(
            self.table.created_at, order=Order.desc,
        ).limit(limit).offset(offset)
        rows = await self.fetch(q)
        total = await self.fetchval(
            self.select(Count('*')).where(self.table.endpoint_id == endpoint_id),
        )
        return [dict(r) for r in rows], total or 0

    async def count_by_endpoints(self, endpoint_ids):
        """Per-endpoint status counts keyed by endpoint id (dashboard list)."""
        if not endpoint_ids:
            return {}
        q = self.select(
            self.table.endpoint_id, self.table.status, Count('*').as_('n'),
        ).where(self.table.endpoint_id.isin(list(endpoint_ids))).groupby(
            self.table.endpoint_id, self.table.status,
        )
        rows = await self.fetch(q)
        counts: dict[str, dict[str, int]] = {}
        for r in rows:
            counts.setdefault(r['endpoint_id'], {})[r['status']] = r['n']
        return counts

    async def metrics_by_endpoint(self, endpoint_id, period='24 hours'):
        """Status counts, error total and avg processing latency (ms) over the
        period. Latency is measured on PROCESSED rows (processed_at−created_at)
        so retries and FAILED rows never distort the SLO view (S3-15).
        endpoint_id is a validated UUID (handlers 404 on non-UUID ids) and
        period comes from a fixed map, so both are safe to inline."""
        interval = f"now() - interval '{period}'"
        counts: dict[str, int] = {}
        for r in await self.fetch(
            f'SELECT status, count(*) AS n FROM {self.name} '
            f"WHERE endpoint_id = '{endpoint_id}' AND created_at >= {interval} GROUP BY status",
        ):
            counts[r['status']] = r['n']
        avg = await self.fetchval(
            f'SELECT AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) * 1000 '
            f"FROM {self.name} WHERE endpoint_id = '{endpoint_id}' AND status = 'PROCESSED' "
            f'AND processed_at IS NOT NULL AND created_at >= {interval}',
        )
        return {
            'counts': counts,
            'errors': counts.get('FAILED', 0),
            'avg_latency_ms': round(float(avg), 2) if avg is not None else None,
        }


class RisInterfaceEndpoints(Table):
    name = 'ris_interface_endpoints'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_interface_endpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            name TEXT NOT NULL,
            interface_type TEXT NOT NULL
                CHECK (interface_type IN ('HL7_ADT', 'HL7_ORM', 'HL7_ORU',
                                          'DICOM_MWL', 'DICOM_MPPS', 'FHIR')),
            protocol TEXT NOT NULL CHECK (protocol IN ('HL7V2', 'DICOM', 'FHIR')),
            config JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            last_message_at TIMESTAMPTZ,
            message_count BIGINT DEFAULT 0,
            error_count BIGINT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)

    async def create(self, data):
        # ::jsonb cast — see RisHl7Messages.create for why raw SQL + params.
        return await self.conn.fetchval(
            'INSERT INTO ris_interface_endpoints '
            '(tenant_id, name, interface_type, protocol, config) '
            'VALUES ($1, $2, $3, $4, $5::jsonb) RETURNING id',
            get_tenant_slug() or 'default',
            data['name'],
            data['interface_type'],
            data['protocol'],
            _json_dumps(data.get('config', {})),
        )

    async def list(self):
        q = self.select('*').orderby(self.table.name)
        rows = await self.fetch(q)
        return [dict(r) for r in rows]

    async def get(self, endpoint_id):
        q = self.select('*').where(self.table.id == endpoint_id)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def get_by_name(self, name):
        q = self.select('*').where(self.table.name == name)
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def touch(self, endpoint_id, status='ok'):
        """Record message flow on the endpoint (dashboard counters).

        Table.exec() takes no query params, so the id is interpolated —
        safe because endpoint_id is a UUID (validated by _require_uuid or
        produced by our own SELECT ... RETURNING id).
        """
        if status == 'ok':
            await self.exec(
                'UPDATE ris_interface_endpoints SET message_count = message_count + 1, '
                f"last_message_at = now() WHERE id = '{endpoint_id}'",
            )
        else:
            await self.exec(
                'UPDATE ris_interface_endpoints SET message_count = message_count + 1, '
                f"error_count = error_count + 1, last_message_at = now() WHERE id = '{endpoint_id}'",
            )


class RisInterfaceEvents(Table):
    name = 'ris_interface_events'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_interface_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            endpoint_id UUID REFERENCES ris_interface_endpoints(id),
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL
                CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
            message TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_interface_events_tenant
            ON ris_interface_events (tenant_id, created_at)
        """)

    async def create(self, data):
        # ::jsonb cast — see RisHl7Messages.create for why raw SQL + params.
        await self.conn.execute(
            'INSERT INTO ris_interface_events '
            '(tenant_id, endpoint_id, event_type, severity, message, metadata) '
            'VALUES ($1, $2, $3, $4, $5, $6::jsonb)',
            get_tenant_slug() or 'default',
            data.get('endpoint_id'),
            data['event_type'],
            data['severity'],
            data['message'],
            _json_dumps(data.get('metadata', {})),
        )