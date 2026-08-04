import re
from datetime import timedelta

from db.table import Table


def period_to_interval(period: str) -> timedelta:
    # asyncpg encodes interval params from timedelta only; '24 hours' strings
    # raise DataError. Default to 24h for unknown/malformed values.
    m = re.match(r'(\d+)\s*(\w+)', str(period))
    if not m:
        return timedelta(hours=24)
    amount = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith('d'):
        return timedelta(days=amount)
    if unit.startswith('h'):
        return timedelta(hours=amount)
    if unit.startswith('m'):
        return timedelta(minutes=amount)
    if unit.startswith('w'):
        return timedelta(weeks=amount)
    return timedelta(hours=24)


class Hl7Message(Table):
    name = 'hl7_messages'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS hl7_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            raw_hash TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            message_type TEXT DEFAULT '',
            event_type TEXT DEFAULT '',
            patient_id TEXT DEFAULT '',
            accession_number TEXT DEFAULT '',
            sending_facility TEXT DEFAULT '',
            parsed_fields JSONB,
            parse_status TEXT NOT NULL DEFAULT 'ok'
                CHECK (parse_status IN ('ok', 'partial', 'failed')),
            error_message TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("CREATE INDEX IF NOT EXISTS ix_hl7_messages_hash ON hl7_messages(raw_hash)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_hl7_messages_type ON hl7_messages(message_type, event_type)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_hl7_messages_patient ON hl7_messages(patient_id)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_hl7_messages_created ON hl7_messages(created_at)")

    async def create(self, data):
        q = self.insert().columns(
            'raw_hash', 'raw_content', 'message_type', 'event_type',
            'patient_id', 'accession_number', 'sending_facility',
            'parsed_fields', 'parse_status', 'error_message',
        ).insert((
            data['raw_hash'],
            data['raw_content'],
            data.get('message_type', ''),
            data.get('event_type', ''),
            data.get('patient_id', ''),
            data.get('accession_number', ''),
            data.get('sending_facility', ''),
            data.get('parsed_fields'),
            data.get('parse_status', 'ok'),
            data.get('error_message', ''),
        ),).returning('id')
        return await self.fetchval(q)

    async def get_messages(self, limit=50, offset=0, message_type='', parse_status='',
                           patient_id='', sending_facility=''):
        conds = []
        vals = []
        idx = 1
        if message_type:
            conds.append(f'message_type = ${idx}')
            vals.append(message_type)
            idx += 1
        if parse_status:
            conds.append(f'parse_status = ${idx}')
            vals.append(parse_status)
            idx += 1
        if patient_id:
            conds.append(f'patient_id ILIKE ${idx}')
            vals.append(f'%{patient_id}%')
            idx += 1
        if sending_facility:
            conds.append(f'sending_facility ILIKE ${idx}')
            vals.append(f'%{sending_facility}%')
            idx += 1
        where = ' AND '.join(conds) if conds else 'TRUE'

        rows = await self.conn.fetch(f"""
            SELECT id, message_type, event_type, patient_id, accession_number,
                   sending_facility, parse_status, error_message, created_at
            FROM hl7_messages
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *vals, limit, offset)
        total = await self.conn.fetchval(f"""
            SELECT COUNT(*) FROM hl7_messages WHERE {where}
        """, *vals)
        return [dict(r) for r in rows], total or 0

    async def get_by_id(self, msg_id):
        row = await self.fetchone(
            self.select(
                'id', 'raw_content', 'message_type', 'event_type',
                'patient_id', 'accession_number', 'sending_facility',
                'parsed_fields', 'parse_status', 'error_message', 'created_at'
            ).where(self.table.id == msg_id)
        )
        return dict(row) if row else None

    async def get_errors_for_message(self, msg_id):
        rows = await self.conn.fetch(
            'SELECT * FROM hl7_parse_errors WHERE hl7_message_id = $1 ORDER BY created_at',
            msg_id
        )
        return [dict(r) for r in rows]

    async def get_metrics(self, period='24 hours'):
        period = period_to_interval(period)
        total = await self.conn.fetchval(
            'SELECT COUNT(*) FROM hl7_messages WHERE created_at > now() - $1::interval', period
        )
        by_type = await self.conn.fetch("""
            SELECT message_type, event_type, COUNT(*) AS count
            FROM hl7_messages
            WHERE created_at > now() - $1::interval
            GROUP BY message_type, event_type
            ORDER BY count DESC
        """, period)
        by_status = await self.conn.fetch("""
            SELECT parse_status, COUNT(*) AS count
            FROM hl7_messages
            WHERE created_at > now() - $1::interval
            GROUP BY parse_status
        """, period)
        by_facility = await self.conn.fetch("""
            SELECT sending_facility, COUNT(*) AS count
            FROM hl7_messages
            WHERE created_at > now() - $1::interval AND sending_facility != ''
            GROUP BY sending_facility
            ORDER BY count DESC
            LIMIT 10
        """, period)
        return {
            'total': total or 0,
            'by_type': [dict(r) for r in by_type],
            'by_status': [dict(r) for r in by_status],
            'by_facility': [dict(r) for r in by_facility],
        }


class Hl7ParseError(Table):
    name = 'hl7_parse_errors'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS hl7_parse_errors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            hl7_message_id UUID REFERENCES hl7_messages(id) ON DELETE CASCADE,
            segment TEXT DEFAULT '',
            field_number INT DEFAULT 0,
            field_name TEXT DEFAULT '',
            raw_value TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("CREATE INDEX IF NOT EXISTS ix_hl7_parse_errors_msg ON hl7_parse_errors(hl7_message_id)")

    async def create(self, data):
        q = self.insert().columns(
            'hl7_message_id', 'segment', 'field_number',
            'field_name', 'raw_value', 'error_message',
        ).insert((
            data['hl7_message_id'],
            data.get('segment', ''),
            int(data.get('field_number', 0)),
            data.get('field_name', ''),
            data.get('raw_value', ''),
            data.get('error_message', ''),
        ),)
        await self.exec(q)
