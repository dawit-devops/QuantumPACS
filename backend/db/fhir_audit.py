from db.table import Table


class FhirAudit(Table):
    name = 'fhir_audit'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS fhir_audit (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER DEFAULT 0,
            method TEXT NOT NULL DEFAULT '',
            path TEXT NOT NULL DEFAULT '',
            query_params TEXT DEFAULT '',
            resource_type TEXT DEFAULT '',
            resource_id TEXT DEFAULT '',
            status_code INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            ip_address TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("CREATE INDEX IF NOT EXISTS ix_fhir_audit_created ON fhir_audit(created_at)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_fhir_audit_user ON fhir_audit(user_id)")
        await self.exec("CREATE INDEX IF NOT EXISTS ix_fhir_audit_resource ON fhir_audit(resource_type, resource_id)")

    async def log_request(self, data):
        q = self.insert().columns(
            'user_id', 'method', 'path', 'query_params',
            'resource_type', 'resource_id', 'status_code',
            'duration_ms', 'ip_address',
        ).insert((
            data.get('user_id', 0),
            data.get('method', ''),
            data.get('path', ''),
            data.get('query_params', ''),
            data.get('resource_type', ''),
            data.get('resource_id', ''),
            data.get('status_code', 0),
            int(data.get('duration_ms', 0)),
            data.get('ip_address', ''),
        ),)
        await self.exec(q)
