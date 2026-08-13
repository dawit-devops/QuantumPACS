"""Report + peer-review tables for the R12 Staff Radiologist workflow.

Schema covers the reading worklist (FR-R12-01), structured reporting
(FR-R12-09) and peer review:
- reports: one row per exam; status machine draft -> preliminary -> final
- report_templates: modality templates for findings/impression (FR-R12-09)
- peer_reviews: assignment + discrepancy-level review of a signed report
"""
from datetime import datetime, timezone

from db.table import Table


class Reports(Table):
    name = 'reports'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'preliminary', 'final')),
            findings TEXT DEFAULT '',
            impression TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            template_name TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            signed_by TEXT DEFAULT '',
            signed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_exam ON reports(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_reports_status ON reports(status)
        """)

    async def create(self, exam_id, data, created_by):
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'exam_id', 'status', 'findings', 'impression', 'recommendations',
            'template_name', 'created_by', 'signed_by', 'created_at', 'updated_at',
        ).insert((
            exam_id,
            data.get('status', 'draft'),
            data.get('findings', ''),
            data.get('impression', ''),
            data.get('recommendations', ''),
            data.get('template_name', ''),
            created_by,
            data.get('signed_by', ''),
            now, now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create report')
        return await self.get(row['id'])

    async def get(self, report_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM reports WHERE id = $1", report_id,
        )
        return dict(row) if row else None

    async def get_by_exam(self, exam_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM reports WHERE exam_id = $1", exam_id,
        )
        return dict(row) if row else None

    async def update(self, report_id, data):
        """Update draft fields (findings/impression/status)."""
        fields = ['updated_at']
        values = [datetime.now(timezone.utc)]
        for k in ('status', 'findings', 'impression', 'recommendations', 'template_name'):
            if k in data:
                fields.append(k)
                values.append(data[k])
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        await self.conn.execute(
            f"UPDATE reports SET {set_clause} WHERE id = $1",
            report_id, *values,
        )
        return await self.get(report_id)

    async def sign(self, report_id, signed_by):
        """Transition to final with the signing radiologist recorded."""
        await self.conn.execute(
            "UPDATE reports SET status = 'final', signed_by = $2, signed_at = now(), "
            "updated_at = now() WHERE id = $1",
            report_id, signed_by,
        )
        return await self.get(report_id)

    async def reading_list(self, status=None, modality=None, search=None,
                            radiologist=None, physician=None,
                            date_from=None, date_to=None):
        """Exams handed off to the reading worklist that lack a final report.

        A study is "ready to read" when the technologist completed it (handoff,
        FR-R06-07) and no final report exists yet. Draft/preliminary reports keep
        the study on the list; a signed final report removes it.

        ME-04: the list is filterable per radiologist (assigned_radiologist),
        by referring physician, and by handoff date range.
        """
        where = [
            "e.status = 'completed'",
            "(r.status IS NULL OR r.status != 'final')",
        ]
        params = []
        idx = 1
        if status:
            where.append(f"r.status IS DISTINCT FROM NULL AND r.status = ${idx}")
            params.append(status)
            idx += 1
        if modality:
            where.append(f"e.modality = ${idx}")
            params.append(modality)
            idx += 1
        if search:
            like = f'%{search}%'
            where.append(
                f"(e.patient_name ILIKE ${idx} OR e.patient_id ILIKE ${idx + 1} "
                f"OR e.accession_number ILIKE ${idx + 2})"
            )
            params.extend([like, like, like])
            idx += 3
        if radiologist:
            where.append(f"e.assigned_radiologist = ${idx}")
            params.append(radiologist)
            idx += 1
        if physician:
            where.append(f"e.referring_physician ILIKE ${idx}")
            params.append(f'%{physician}%')
            idx += 1
        if date_from:
            where.append(f"e.completed_at >= ${idx}::timestamptz")
            params.append(f'{date_from}T00:00:00+00:00')
            idx += 1
        if date_to:
            where.append(f"e.completed_at <= ${idx}::timestamptz")
            params.append(f'{date_to}T23:59:59.999+00:00')
            idx += 1

        q = f"""
            SELECT e.id AS exam_id, e.patient_id, e.patient_name, e.patient_birth_date,
                   e.patient_sex, e.accession_number, e.requested_procedure_desc,
                   e.modality, e.priority, e.protocol_name, e.completed_at,
                   e.assigned_technologist, e.assigned_radiologist,
                   e.referring_physician,
                   r.id AS report_id, r.status AS report_status,
                   r.signed_by, r.signed_at
            FROM exams e
            LEFT JOIN reports r ON r.exam_id = e.id
            WHERE {' AND '.join(where)}
        """
        rows = await self.conn.fetch(q, *params)
        items = [dict(r) for r in rows]
        # STAT first, then urgent, then routine; oldest completed first within a tier
        # (FIFO reading queue keeps turnaround predictable per M-R12 turnaround SLAs).
        priority_order = {'stat': 0, 'urgent': 1, 'routine': 2}
        items.sort(key=lambda r: (
            priority_order.get(r.get('priority') or 'routine', 9),
            r.get('completed_at') or datetime.max.replace(tzinfo=timezone.utc),
        ))
        return items


class ReportTemplates(Table):
    name = 'report_templates'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS report_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            modality TEXT NOT NULL,
            body_part TEXT DEFAULT '',
            findings_template TEXT DEFAULT '',
            impression_template TEXT DEFAULT '',
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_report_templates_modality ON report_templates(modality)
        """)

    async def list_by_modality(self, modality=None):
        if modality:
            rows = await self.conn.fetch(
                "SELECT * FROM report_templates WHERE modality = $1 ORDER BY name",
                modality,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM report_templates ORDER BY modality, name",
            )
        return [dict(r) for r in rows]

    async def count(self):
        return await self.conn.fetchval('SELECT count(*) FROM report_templates') or 0


class PeerReviews(Table):
    name = 'peer_reviews'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS peer_reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id UUID NOT NULL,
            reviewer_id TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'assigned'
                CHECK (status IN ('assigned', 'in_progress', 'completed')),
            discrepancy_level TEXT DEFAULT ''
                CHECK (discrepancy_level IN ('', 'none', 'minor', 'major', 'discrepancy')),
            comment TEXT DEFAULT '',
            assigned_at TIMESTAMPTZ DEFAULT now(),
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_peer_reviews_reviewer ON peer_reviews(reviewer_id, status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_peer_reviews_report ON peer_reviews(report_id)
        """)

    async def create(self, report_id, reviewer_id):
        q = self.insert().columns(
            'report_id', 'reviewer_id', 'status',
        ).insert((report_id, reviewer_id, 'assigned')).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create peer review')
        return await self.get(row['id'])

    async def get(self, review_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM peer_reviews WHERE id = $1", review_id,
        )
        return dict(row) if row else None

    async def list_for_reviewer(self, reviewer_id, status=None):
        where = ["reviewer_id = $1"]
        params = [reviewer_id]
        if status:
            where.append("status = $2")
            params.append(status)
        rows = await self.conn.fetch(
            f"SELECT * FROM peer_reviews WHERE {' AND '.join(where)} ORDER BY created_at DESC",
            *params,
        )
        return [dict(r) for r in rows]

    async def start(self, review_id):
        await self.conn.execute(
            "UPDATE peer_reviews SET status = 'in_progress' WHERE id = $1",
            review_id,
        )

    async def submit(self, review_id, discrepancy_level, comment):
        await self.conn.execute(
            "UPDATE peer_reviews SET status = 'completed', discrepancy_level = $2, "
            "comment = $3, completed_at = now() WHERE id = $1",
            review_id, discrepancy_level, comment,
        )
        return await self.get(review_id)
