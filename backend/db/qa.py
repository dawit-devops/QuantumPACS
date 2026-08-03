"""QA tables for the R05 QI/QA Team workflow.

Covers the QA review queue (FR-R05-01/02), protocol compliance scorecard data
(FR-R05-03/04), corrective actions (FR-R05-05) and QA incident logging
(FR-R05-06):

- qa_scores: one row per reviewed exam; feeds the R03 compliance scorecard
- corrective_actions: R03/R05/R06-sourced actions assigned to the QA team
- incidents: existing R06 table extended with resolved status + study UIDs
- protocols: existing R06 registry extended with protocol_code + ACR benchmarks
"""
from datetime import datetime, timezone

from db.table import Table


class QaScores(Table):
    name = 'qa_scores'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS qa_scores (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            protocol_id UUID,
            pass_fail TEXT NOT NULL DEFAULT 'pass'
                CHECK (pass_fail IN ('pass', 'fail', 'skipped')),
            discrepancy_level TEXT NOT NULL DEFAULT 'none'
                CHECK (discrepancy_level IN ('none', 'minor', 'major', 'critical')),
            dose_dlp FLOAT DEFAULT 0,
            dose_ctdivol FLOAT DEFAULT 0,
            dose_kvp FLOAT DEFAULT 0,
            dose_mas FLOAT DEFAULT 0,
            sequence_compliance JSONB DEFAULT '{}'::jsonb,
            comments TEXT DEFAULT '',
            reviewed_by TEXT DEFAULT '',
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_qa_scores_exam ON qa_scores(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_qa_scores_reviewed ON qa_scores(reviewed_at)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        import json as _json
        q = self.insert().columns(
            'exam_id', 'protocol_id', 'pass_fail', 'discrepancy_level',
            'dose_dlp', 'dose_ctdivol', 'dose_kvp', 'dose_mas',
            'sequence_compliance', 'comments', 'reviewed_by', 'reviewed_at',
        ).insert((
            data['exam_id'],
            data.get('protocol_id'),
            data.get('pass_fail', 'pass'),
            data.get('discrepancy_level', 'none'),
            data.get('dose_dlp', 0),
            data.get('dose_ctdivol', 0),
            data.get('dose_kvp', 0),
            data.get('dose_mas', 0),
            _json.dumps(data.get('sequence_compliance') or {}),
            data.get('comments', ''),
            data.get('reviewed_by', ''),
            data.get('reviewed_at') or now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create QA score')
        return await self.get(row['id'])

    async def get(self, score_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM qa_scores WHERE id = $1", score_id,
        )
        return dict(row) if row else None

    async def get_by_exam(self, exam_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM qa_scores WHERE exam_id = $1", exam_id,
        )
        return dict(row) if row else None

    async def compliance_summary(self, modality=None, protocol_id=None):
        """Aggregate pass/fail compliance for the R03 scorecard (FR-R05-04)."""
        where = []
        params = []
        idx = 1
        if modality:
            where.append(f"e.modality = ${idx}")
            params.append(modality)
            idx += 1
        if protocol_id:
            where.append(f"q.protocol_id = ${idx}")
            params.append(protocol_id)
            idx += 1
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = await self.conn.fetch(
            f"""SELECT e.modality, q.protocol_id, q.pass_fail,
                       COUNT(*) AS n
                FROM qa_scores q
                JOIN exams e ON e.id = q.exam_id
                {clause}
                GROUP BY e.modality, q.protocol_id, q.pass_fail""",
            *params,
        )
        return [dict(r) for r in rows]

    async def count(self):
        return await self.conn.fetchval('SELECT count(*) FROM qa_scores') or 0


class CorrectiveActions(Table):
    name = 'corrective_actions'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS corrective_actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source TEXT NOT NULL DEFAULT 'R05_self'
                CHECK (source IN ('R03', 'R05_self', 'R06')),
            issue TEXT NOT NULL,
            study_uids JSONB DEFAULT '[]'::jsonb,
            assigned_to TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'resolved')),
            findings TEXT DEFAULT '',
            actions_taken TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_corrective_actions_status
            ON corrective_actions(status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_corrective_actions_assigned
            ON corrective_actions(assigned_to)
        """)

    async def create(self, data):
        import json as _json
        q = self.insert().columns(
            'source', 'issue', 'study_uids', 'assigned_to', 'status',
            'findings', 'actions_taken', 'created_by',
        ).insert((
            data.get('source', 'R05_self'),
            data['issue'],
            _json.dumps(data.get('study_uids') or []),
            data.get('assigned_to', ''),
            data.get('status', 'open'),
            data.get('findings', ''),
            data.get('actions_taken', ''),
            data.get('created_by', ''),
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create corrective action')
        return await self.get(row['id'])

    async def get(self, action_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM corrective_actions WHERE id = $1", action_id,
        )
        return dict(row) if row else None

    async def list(self, status=None):
        if status:
            rows = await self.conn.fetch(
                "SELECT * FROM corrective_actions WHERE status = $1 "
                "ORDER BY created_at DESC",
                status,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM corrective_actions ORDER BY created_at DESC",
            )
        return [dict(r) for r in rows]

    async def resolve(self, action_id, findings, actions_taken):
        await self.conn.execute(
            "UPDATE corrective_actions SET status = 'resolved', findings = $2, "
            "actions_taken = $3, resolved_at = now() WHERE id = $1",
            action_id, findings, actions_taken,
        )
        return await self.get(action_id)

    async def count_open(self):
        return await self.conn.fetchval(
            "SELECT count(*) FROM corrective_actions WHERE status != 'resolved'",
        ) or 0


class IncidentsQA(Table):
    """QA-facing views over the R06 `incidents` table (FR-R05-06)."""

    name = 'incidents'

    async def sync_db(self):
        # Extend the R06 incidents table with the QA-resolved lifecycle and
        # study UID links. ALTER IF NOT EXISTS-style guards keep this idempotent.
        for stmt in (
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS study_uid TEXT DEFAULT ''",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS repeat_study_uid TEXT DEFAULT ''",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open' "
            "CHECK (status IN ('open', 'in_progress', 'resolved'))",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolution_notes TEXT DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_incidents_status ON incidents(status)",
            "CREATE INDEX IF NOT EXISTS ix_incidents_type ON incidents(incident_type)",
        ):
            await self.exec(stmt)

    async def create(self, data):
        q = self.insert().columns(
            'exam_id', 'incident_type', 'severity', 'description', 'reported_by',
        ).insert((
            data['exam_id'], data['incident_type'], data['severity'],
            data['description'], data.get('reported_by', ''),
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create incident')
        return await self.get(row['id'])

    async def get(self, incident_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM incidents WHERE id = $1", incident_id,
        )
        return dict(row) if row else None

    async def list(self, incident_type=None, status=None, search=None):
        where = []
        params = []
        idx = 1
        if incident_type:
            where.append(f"i.incident_type = ${idx}")
            params.append(incident_type)
            idx += 1
        if status:
            where.append(f"i.status = ${idx}")
            params.append(status)
            idx += 1
        if search:
            like = f'%{search}%'
            where.append(
                f"(e.accession_number ILIKE ${idx} OR e.patient_name ILIKE ${idx} "
                f"OR i.study_uid ILIKE ${idx})"
            )
            params.extend([like, like, like])
            idx += 3
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = await self.conn.fetch(
            f"""SELECT i.*, e.accession_number, e.patient_name, e.modality
                FROM incidents i
                LEFT JOIN exams e ON e.id = i.exam_id
                {clause}
                ORDER BY i.created_at DESC""",
            *params,
        )
        return [dict(r) for r in rows]

    async def mark_resolved(self, incident_id, notes):
        await self.conn.execute(
            "UPDATE incidents SET status = 'resolved', resolution_notes = $2, "
            "resolved_at = now() WHERE id = $1",
            incident_id, notes,
        )


class ProtocolsQA(Table):
    """QA protocol registry CRUD over the R06 `protocols` table (FR-R05-03)."""

    name = 'protocols'

    async def sync_db(self):
        for stmt in (
            "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS protocol_code TEXT DEFAULT ''",
            "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS acr_benchmark_ctdivol FLOAT",
            "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS acr_benchmark_min_snr FLOAT",
            "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()",
            # Partial unique index: only enforce uniqueness when a code is set
            # (seeded R06 protocols have empty codes).
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_protocols_code "
            "ON protocols(protocol_code) WHERE protocol_code != ''",
        ):
            await self.exec(stmt)

    async def list_all(self, modality=None, search=None):
        where = []
        params = []
        idx = 1
        if modality:
            where.append(f"modality = ${idx}")
            params.append(modality)
            idx += 1
        if search:
            like = f'%{search}%'
            where.append(f"(name ILIKE ${idx} OR protocol_code ILIKE ${idx})")
            params.append(like)
            idx += 1
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = await self.conn.fetch(
            f"SELECT * FROM protocols {clause} ORDER BY modality, name",
            *params,
        )
        return [dict(r) for r in rows]

    async def get_by_code(self, code):
        row = await self.conn.fetchrow(
            "SELECT * FROM protocols WHERE protocol_code = $1", code,
        )
        return dict(row) if row else None

    async def create(self, data):
        import json as _json
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'name', 'protocol_code', 'modality', 'body_part', 'sequences',
            'parameters', 'acr_benchmark_dlp', 'acr_benchmark_ctdivol',
            'acr_benchmark_min_snr', 'is_default', 'updated_at',
        ).insert((
            data['name'], data.get('protocol_code', ''), data['modality'],
            data.get('body_part', ''),
            _json.dumps(data.get('sequences') or []),
            _json.dumps(data.get('parameters') or {}),
            data.get('acr_benchmark_dlp'),
            data.get('acr_benchmark_ctdivol'),
            data.get('acr_benchmark_min_snr'),
            data.get('is_default', False),
            now,
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create protocol')
        return await self.get(row['id'])

    async def get(self, protocol_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM protocols WHERE id = $1", protocol_id,
        )
        return dict(row) if row else None

    async def update(self, protocol_id, data):
        import json as _json
        fields = ['updated_at']
        values = [datetime.now(timezone.utc)]
        for col in ('name', 'protocol_code', 'modality', 'body_part',
                    'acr_benchmark_dlp', 'acr_benchmark_ctdivol',
                    'acr_benchmark_min_snr', 'is_default'):
            if col in data:
                fields.append(col)
                values.append(data[col])
        if 'sequences' in data:
            fields.append('sequences')
            values.append(_json.dumps(data['sequences']))
        if 'parameters' in data:
            fields.append('parameters')
            values.append(_json.dumps(data['parameters']))
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        await self.conn.execute(
            f"UPDATE protocols SET {set_clause} WHERE id = $1",
            protocol_id, *values,
        )
        return await self.get(protocol_id)

    async def delete(self, protocol_id):
        await self.conn.execute(
            "DELETE FROM protocols WHERE id = $1", protocol_id,
        )
