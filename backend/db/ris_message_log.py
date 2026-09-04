"""RIS Reminders DB Layer (R2-02).

ris_message_log records every outbound reminder delivery (SMS/email/phone)
with status SENT/FAILED, attempt count and provider receipt — the retry
loop and the <= 5-minute failure alert both read it. ris_reminder_config
stores per-tenant channel + template + lead-time settings the frontend
edits (R2-01-10).
"""

from db.table import Table


class MessageLog(Table):
    name = 'ris_message_log'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_message_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            channel TEXT NOT NULL DEFAULT 'email'
                CHECK (channel IN ('sms', 'email', 'phone')),
            recipient TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL DEFAULT '',
            subject TEXT DEFAULT '',
            body TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'SENT'
                CHECK (status IN ('SENT', 'FAILED')),
            attempts INTEGER NOT NULL DEFAULT 1,
            provider_receipt TEXT DEFAULT '',
            sent_at TIMESTAMPTZ DEFAULT now(),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)

    async def log_sent(self, *, channel, recipient, event_type,
                       subject='', body='', provider_receipt='',
                       tenant_id='default'):
        return await self.conn.fetchrow(
            "INSERT INTO ris_message_log"
            " (tenant_id, channel, recipient, event_type, subject, body,"
            "  status, attempts, provider_receipt)"
            " VALUES ($1, $2, $3, $4, $5, $6, 'SENT', 1, $7)"
            " RETURNING id, status",
            tenant_id, channel, recipient, event_type, subject, body,
            provider_receipt,
        )

    async def log_failed(self, *, channel, recipient, event_type,
                         subject='', body='', attempts=1, tenant_id='default'):
        return await self.conn.fetchrow(
            "INSERT INTO ris_message_log"
            " (tenant_id, channel, recipient, event_type, subject, body,"
            "  status, attempts)"
            " VALUES ($1, $2, $3, $4, $5, $6, 'FAILED', $7)"
            " RETURNING id, status",
            tenant_id, channel, recipient, event_type, subject, body, attempts,
        )

    async def bump_attempt(self, message_id):
        await self.conn.execute(
            "UPDATE ris_message_log SET attempts = attempts + 1,"
            " updated_at = now() WHERE id = $1 AND status = 'FAILED'",
            message_id,
        )

    async def list(self, tenant_id='default', status=None, limit=100, offset=0):
        conditions = ['tenant_id = $1']
        params = [tenant_id]
        idx = 2
        if status:
            conditions.append(f'status = ${idx}')
            params.append(status)
            idx += 1
        where = ' AND '.join(conditions)
        rows = await self.conn.fetch(
            f"SELECT id, channel, recipient, event_type, subject, status,"
            f" attempts, provider_receipt, sent_at"
            f" FROM ris_message_log WHERE {where}"
            f" ORDER BY sent_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params, limit, offset,
        )
        total = await self.conn.fetchval(
            f"SELECT count(*) FROM ris_message_log WHERE {where}",
            *params,
        )
        return [dict(r) for r in rows], total or 0

    async def failed_since(self, minutes=5, tenant_id='default'):
        """FAILED messages in the last `minutes` — the <= 5-min alert window."""
        return await self.conn.fetch(
            "SELECT id, channel, recipient, event_type, attempts, sent_at"
            " FROM ris_message_log"
            " WHERE tenant_id = $1 AND status = 'FAILED'"
            "   AND sent_at >= now() - make_interval(mins => $2)",
            tenant_id, minutes,
        )


class ReminderConfig(Table):
    name = 'ris_reminder_config'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_reminder_config (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            event_type TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'email'
                CHECK (channel IN ('sms', 'email', 'phone')),
            template TEXT DEFAULT '',
            lead_time_hours INTEGER NOT NULL DEFAULT 24,
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (tenant_id, event_type)
        )
        """)

    async def upsert(self, *, event_type, channel, template='',
                     lead_time_hours=24, active=True, tenant_id='default'):
        await self.conn.execute(
            "INSERT INTO ris_reminder_config"
            " (tenant_id, event_type, channel, template, lead_time_hours, active)"
            " VALUES ($1, $2, $3, $4, $5, $6)"
            " ON CONFLICT (tenant_id, event_type)"
            " DO UPDATE SET channel = EXCLUDED.channel,"
            " template = EXCLUDED.template,"
            " lead_time_hours = EXCLUDED.lead_time_hours,"
            " active = EXCLUDED.active, updated_at = now()",
            tenant_id, event_type, channel, template, lead_time_hours, active,
        )

    async def get(self, event_type, tenant_id='default'):
        return await self.conn.fetchrow(
            "SELECT * FROM ris_reminder_config"
            " WHERE tenant_id = $1 AND event_type = $2",
            tenant_id, event_type,
        )

    async def list_active(self, tenant_id='default'):
        return await self.conn.fetch(
            "SELECT * FROM ris_reminder_config"
            " WHERE tenant_id = $1 AND active"
            " ORDER BY event_type",
            tenant_id,
        )


class PatientOptOut(Table):
    """CS4/CC-12: per-patient reminder opt-out registry.

    A row with event_type NULL opts the patient out of ALL events; a typed
    row covers one event. The COALESCE unique index keeps either shape
    single-instance per (tenant, patient)."""

    name = 'patient_reminder_optouts'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS patient_reminder_optouts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id TEXT NOT NULL,
            event_type TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now(),
            created_by TEXT DEFAULT ''
        )
        """)
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_optout
        ON patient_reminder_optouts (tenant_id, patient_id,
                                     COALESCE(event_type, ''))
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_patient_optout_patient
        ON patient_reminder_optouts(patient_id)
        """)

    async def opt_out(self, *, patient_id, event_type=None, by='',
                      tenant_id='default'):
        await self.sync_db()
        await self.conn.execute(
            """INSERT INTO patient_reminder_optouts
               (patient_id, event_type, tenant_id, created_by)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT DO NOTHING""",
            str(patient_id), event_type, tenant_id, str(by or ''),
        )

    async def remove_opt_out(self, *, patient_id, event_type=None,
                             tenant_id='default'):
        await self.conn.execute(
            """DELETE FROM patient_reminder_optouts
               WHERE tenant_id = $1 AND patient_id = $2
                 AND COALESCE(event_type, '') = COALESCE($3, '')""",
            tenant_id, str(patient_id), event_type,
        )

    async def is_opted_out(self, patient_id, event_type,
                           tenant_id='default'):
        """True when the patient declined this event or all events."""
        row = await self.conn.fetchval(
            """SELECT 1 FROM patient_reminder_optouts
               WHERE tenant_id = $1 AND patient_id = $2
                 AND (event_type IS NULL OR event_type = $3)
               LIMIT 1""",
            tenant_id, str(patient_id), event_type,
        )
        return bool(row)

    async def list_all(self, tenant_id='default', limit=200):
        rows = await self.conn.fetch(
            "SELECT * FROM patient_reminder_optouts"
            " WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2",
            tenant_id, max(int(limit), 1),
        )
        return [dict(r) for r in rows]
