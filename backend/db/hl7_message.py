from db.table import Table


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
