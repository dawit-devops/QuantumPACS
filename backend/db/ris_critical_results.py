"""RIS Critical Results DB Layer (S10-01).

Tracks critical findings, ED physician recipients, acknowledgments, and escalations.
"""
from datetime import datetime, timezone
from db.table import Table
from db.conn import get_tenant_slug


class RisCriticalResults(Table):
    name = 'ris_critical_results'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_critical_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id UUID,
            exam_id UUID,
            accession_number TEXT NOT NULL DEFAULT '',
            patient_id TEXT NOT NULL DEFAULT '',
            patient_name TEXT DEFAULT '',
            finding_description TEXT NOT NULL DEFAULT '',
            recipient_id TEXT DEFAULT '',
            recipient_name TEXT DEFAULT '',
            recipient_role TEXT DEFAULT 'ed_physician',
            status TEXT NOT NULL DEFAULT 'flagged'
                CHECK (status IN ('flagged', 'acknowledged', 'escalated', 'cleared')),
            flagged_by TEXT DEFAULT '',
            flagged_at TIMESTAMPTZ DEFAULT now(),
            acknowledged_by TEXT DEFAULT '',
            acknowledged_at TIMESTAMPTZ,
            escalated_at TIMESTAMPTZ,
            escalated_to TEXT DEFAULT '',
            tenant_id TEXT DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_critical_status ON ris_critical_results(status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_critical_accession ON ris_critical_results(accession_number)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_critical_tenant ON ris_critical_results(tenant_id)
        """)

    async def create_flag(self, data, flagged_by):
        """Create a new critical result entry."""
        await self.sync_db()
        now = datetime.now(timezone.utc)
        tenant = get_tenant_slug() or 'default'
        row = await self.conn.fetchrow(
            """INSERT INTO ris_critical_results
               (report_id, exam_id, accession_number, patient_id, patient_name,
                finding_description, recipient_id, recipient_name, recipient_role,
                status, flagged_by, flagged_at, tenant_id, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'flagged', $10, $11, $12, $11, $11)
               RETURNING *""",
            data.get('report_id'), data.get('exam_id'),
            data.get('accession_number', ''), data.get('patient_id', ''),
            data.get('patient_name', ''), data['finding_description'],
            data.get('recipient_id', ''), data.get('recipient_name', ''),
            data.get('recipient_role', 'ed_physician'), str(flagged_by),
            now, tenant,
        )
        return dict(row) if row else None

    async def acknowledge(self, critical_id, acknowledged_by):
        """Acknowledge a critical finding."""
        await self.sync_db()
        now = datetime.now(timezone.utc)
        row = await self.conn.fetchrow(
            """UPDATE ris_critical_results
               SET status = 'acknowledged', acknowledged_by = $2,
                   acknowledged_at = $3, updated_at = $3
               WHERE id = $1
               RETURNING *""",
            critical_id, str(acknowledged_by), now,
        )
        return dict(row) if row else None

    async def escalate(self, critical_id, escalated_to):
        """Escalate an unacknowledged critical finding."""
        await self.sync_db()
        now = datetime.now(timezone.utc)
        row = await self.conn.fetchrow(
            """UPDATE ris_critical_results
               SET status = 'escalated', escalated_to = $2,
                   escalated_at = $3, updated_at = $3
               WHERE id = $1
               RETURNING *""",
            critical_id, str(escalated_to), now,
        )
        return dict(row) if row else None

    async def list_active(self, recipient_id=None, status=None):
        """List active critical findings for a facility or recipient."""
        await self.sync_db()
        where = ["tenant_id = $1"]
        params = [get_tenant_slug() or 'default']
        idx = 2
        if recipient_id:
            where.append(f"(recipient_id = ${idx} OR recipient_id = '')")
            params.append(str(recipient_id))
            idx += 1
        if status:
            where.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        query = f"SELECT * FROM ris_critical_results WHERE {' AND '.join(where)} ORDER BY flagged_at DESC"
        rows = await self.conn.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_unacknowledged_over_minutes(self, minutes=15):
        """Get unacknowledged critical findings older than given minutes for escalation."""
        await self.sync_db()
        delta = timedelta(minutes=minutes)
        rows = await self.conn.fetch(
            """SELECT * FROM ris_critical_results
               WHERE status = 'flagged'
               AND flagged_at <= now() - $1::interval""",
            delta,
        )
        return [dict(r) for r in rows]
