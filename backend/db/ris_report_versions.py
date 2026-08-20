"""RIS Report Versions DB layer (S8-08).

Provides version history logging and diff querying for structured reports.
"""
from datetime import datetime, timezone
from db.table import Table


class RisReportVersions(Table):
    name = 'ris_report_versions'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_report_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id UUID NOT NULL,
            version_number INT NOT NULL DEFAULT 1,
            findings TEXT DEFAULT '',
            impression TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            edited_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_report_versions_report ON ris_report_versions(report_id)
        """)

    async def add_version(self, report_id, findings, impression, recommendations='', edited_by=''):
        """Snapshot current report state as a new version."""
        await self.sync_db()
        next_ver = await self.conn.fetchval(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM ris_report_versions WHERE report_id = $1",
            report_id,
        )
        now = datetime.now(timezone.utc)
        row = await self.conn.fetchrow(
            """INSERT INTO ris_report_versions
               (report_id, version_number, findings, impression, recommendations, edited_by, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               RETURNING *""",
            report_id, next_ver, findings or '', impression or '',
            recommendations or '', str(edited_by or ''), now,
        )
        return dict(row) if row else None

    async def get_history(self, report_id):
        """Retrieve all historical versions for a report, ordered by version number."""
        await self.sync_db()
        rows = await self.conn.fetch(
            "SELECT * FROM ris_report_versions WHERE report_id = $1 ORDER BY version_number ASC",
            report_id,
        )
        return [dict(r) for r in rows]

    async def get_version_diff(self, report_id, v1: int, v2: int):
        """Compare two versions of a report."""
        await self.sync_db()
        row1 = await self.conn.fetchrow(
            "SELECT * FROM ris_report_versions WHERE report_id = $1 AND version_number = $2",
            report_id, v1,
        )
        row2 = await self.conn.fetchrow(
            "SELECT * FROM ris_report_versions WHERE report_id = $1 AND version_number = $2",
            report_id, v2,
        )
        if not row1 or not row2:
            return None
        return {
            'v1': dict(row1),
            'v2': dict(row2),
            'findings_changed': row1['findings'] != row2['findings'],
            'impression_changed': row1['impression'] != row2['impression'],
        }
