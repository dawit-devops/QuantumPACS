"""Report + peer-review tables for the R12 Staff Radiologist workflow.

Schema covers the reading worklist (FR-R12-01), structured reporting
(FR-R12-09) and peer review:
- reports: one row per exam; status machine draft -> preliminary -> final
- report_templates: modality templates for findings/impression (FR-R12-09)
- peer_reviews: assignment + discrepancy-level review of a signed report
"""
from datetime import datetime, timezone

from db.table import Table

# A4 (GAP_AUDIT_TDD_PIPELINE.md): single source for the HIM release gate
# (R2-05-05, migration 084). Patient-bound surfaces must exclude held
# reports; staff-facing reads are unaffected. Alias `r` = reports table.
RELEASE_VISIBLE_SQL = "r.release_status IS DISTINCT FROM 'held'"


class Reports(Table):
    name = 'reports'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'preliminary', 'submitted', 'final')),
            findings TEXT DEFAULT '',
            impression TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            template_name TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            signed_by TEXT DEFAULT '',
            signed_at TIMESTAMPTZ,
            submitted_at TIMESTAMPTZ,
            review_feedback TEXT DEFAULT '',
            reviewed_by TEXT DEFAULT '',
            reviewed_at TIMESTAMPTZ,
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
        await self.exec("""
        ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS ris_order_id UUID,
            ADD COLUMN IF NOT EXISTS template_id UUID,
            ADD COLUMN IF NOT EXISTS distributed_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE
        """)

    async def create(self, exam_id, data, created_by):
        await self.sync_db()
        now = datetime.now(timezone.utc)
        # V-6: template_id / ris_order_id columns exist (ALTER above) but
        # were silently dropped by the INSERT — the report then lost its
        # template and order linkage on the very first save.
        q = self.insert().columns(
            'exam_id', 'status', 'findings', 'impression', 'recommendations',
            'template_name', 'template_id', 'ris_order_id', 'created_by',
            'signed_by', 'is_critical',
            'created_at', 'updated_at',
        ).insert((
            exam_id,
            data.get('status', 'draft'),
            data.get('findings', ''),
            data.get('impression', ''),
            data.get('recommendations', ''),
            data.get('template_name', ''),
            data.get('template_id'),
            data.get('ris_order_id'),
            created_by,
            data.get('signed_by', ''),
            bool(data.get('is_critical', False)),
            now, now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create report')
        return await self.get(row['id'])

    async def get(self, report_id):
        await self.sync_db()
        row = await self.conn.fetchrow(
            "SELECT * FROM reports WHERE id = $1", report_id,
        )
        return dict(row) if row else None

    async def get_by_exam(self, exam_id):
        await self.sync_db()
        row = await self.conn.fetchrow(
            "SELECT * FROM reports WHERE exam_id = $1", exam_id,
        )
        return dict(row) if row else None

    async def update(self, report_id, data, edited_by=''):
        """Update draft fields (findings/impression/status)."""
        await self.sync_db()
        previous = await self.get(report_id)
        fields = ['updated_at']
        values = [datetime.now(timezone.utc)]
        for k in ('status', 'findings', 'impression', 'recommendations', 'template_name', 'template_id', 'ris_order_id', 'is_critical'):
            if k in data:
                fields.append(k)
                values.append(data[k])
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        await self.conn.execute(
            f"UPDATE reports SET {set_clause} WHERE id = $1",
            report_id, *values,
        )
        updated = await self.get(report_id)
        if updated:
            # V-4: only snapshot a version when the content actually
            # changed — an identical PUT (autosave re-fire, no edit) must
            # not add a duplicate row to the version history.
            content_keys = ('findings', 'impression', 'recommendations')
            changed = any(
                (updated.get(k) or '') != (previous or {}).get(k, '')
                for k in content_keys
            )
            if changed:
                try:
                    from db.ris_report_versions import RisReportVersions
                    await RisReportVersions(self.conn).add_version(
                        report_id, updated.get('findings', ''),
                        updated.get('impression', ''), updated.get('recommendations', ''),
                        edited_by=edited_by or updated.get('created_by', ''),
                    )
                except Exception:
                    pass
        return updated

    async def sign(self, report_id, signed_by):
        """Transition to final with the signing radiologist recorded."""
        await self.sync_db()
        now = datetime.now(timezone.utc)
        await self.conn.execute(
            "UPDATE reports SET status = 'final', signed_by = $2, signed_at = $3, "
            "distributed_at = $3, updated_at = $3 WHERE id = $1",
            report_id, signed_by, now,
        )
        updated = await self.get(report_id)
        if updated:
            try:
                from db.ris_report_versions import RisReportVersions
                await RisReportVersions(self.conn).add_version(
                    report_id, updated.get('findings', ''),
                    updated.get('impression', ''), updated.get('recommendations', ''),
                    edited_by=signed_by,
                )
            except Exception:
                pass
        return updated

    async def submit(self, report_id):
        """R13 resident hands a draft to the supervising attending (co-sign).

        Clears any prior return feedback and stamps submitted_at; the report
        is now locked against further edits until the attending signs it or
        returns it for revision.
        """
        await self.conn.execute(
            "UPDATE reports SET status = 'submitted', submitted_at = now(), "
            "review_feedback = '', reviewed_by = '', reviewed_at = NULL, "
            "updated_at = now() WHERE id = $1",
            report_id,
        )
        return await self.get(report_id)

    async def return_report(self, report_id, reviewed_by, feedback):
        """Attending sends a submitted draft back to the resident.

        Status returns to 'draft' (editable again) with the reviewer's
        feedback preserved for the resident's console alert.
        """
        await self.conn.execute(
            "UPDATE reports SET status = 'draft', review_feedback = $3, "
            "reviewed_by = $2, reviewed_at = now(), updated_at = now() "
            "WHERE id = $1",
            report_id, reviewed_by, feedback,
        )
        return await self.get(report_id)

    async def reading_list(self, status=None, modality=None, search=None,
                            radiologist=None, physician=None,
                            date_from=None, date_to=None, review=None):
        """Exams handed off to the reading worklist that lack a final report.

        A study is "ready to read" when the technologist completed it (handoff,
        FR-R06-07) and no final report exists yet. Draft/preliminary reports keep
        the study on the list; a signed final report removes it.

        ME-04: the list is filterable per radiologist (assigned_radiologist),
        by referring physician, and by handoff date range.

        R13 supervision: review=1 narrows the list to reports the residents
        have submitted — the attending's co-sign queue.
        """
        where = [
            "e.status = 'completed'",
            "(r.status IS NULL OR r.status != 'final')",
        ]
        params = []
        idx = 1
        if status:
            # R13 resident revision loop: a "returned" report is a draft the
            # attending sent back with feedback (return_report() resets the
            # status to 'draft' and fills review_feedback), so the filter
            # cannot match r.status alone.
            if status == 'returned':
                where.append(
                    "r.status = 'draft' AND r.review_feedback <> ''"
                )
            else:
                where.append(f"r.status IS DISTINCT FROM NULL AND r.status = ${idx}")
                params.append(status)
                idx += 1
        if review:
            where.append("r.status = 'submitted'")
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
                   e.critical_flag, e.critical_flag_note, e.critical_flagged_at,
                   r.id AS report_id, r.status AS report_status,
                   r.signed_by, r.signed_at, r.submitted_at, r.review_feedback,
                   r.reviewed_by, r.created_by AS report_author
            FROM exams e
            LEFT JOIN reports r ON r.exam_id = e.id
            WHERE {' AND '.join(where)}
        """
        rows = await self.conn.fetch(q, *params)
        items = [dict(r) for r in rows]
        # STAT first, then urgent, then routine; oldest completed first within a tier
        # (FIFO reading queue keeps turnaround predictable per M-R12 turnaround SLAs).
        priority_order = {'stat': 0, 'urgent': 1, 'routine': 2}
        # Critical flags (technologist review P1-1) read ABOVE their priority
        # tier — a flagged study jumps the routine/urgent queue so the alarming
        # finding is seen immediately; within the same flag+priority tier the
        # FIFO order is preserved.
        flag_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        items.sort(key=lambda r: (
            flag_order.get((r.get('critical_flag') or '').lower(), 9),
            priority_order.get(r.get('priority') or 'routine', 9),
            r.get('completed_at') or datetime.max.replace(tzinfo=timezone.utc),
        ))
        return items

    async def _ensure_release_status(self):
        await self.conn.execute(
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS release_status "
            "TEXT NOT NULL DEFAULT 'auto'")

    async def set_release_status(self, report_id, status):
        """R2-05-05: HIM release gate — auto | held | released."""
        if status not in ('auto', 'held', 'released'):
            raise ValueError('release_status must be auto/held/released')
        return await self.conn.fetchrow(
            "UPDATE reports SET release_status = $2 WHERE id::text = $1 "
            "RETURNING id::text AS id, release_status",
            str(report_id), status,
        )


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
