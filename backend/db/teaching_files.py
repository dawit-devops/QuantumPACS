"""Teaching file library (R-11/RES-03).

Curated teaching cases submitted from the reading console: a completed exam
plus the author's teaching points, differential diagnosis and viewer
annotations. Browsable by all reading roles (REPORT_READ), writable by
REPORT_WRITE holders.
"""
from db.table import Table


class TeachingFiles(Table):
    name = 'teaching_files'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS teaching_files (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID,
            title TEXT NOT NULL,
            modality TEXT DEFAULT '',
            body_part TEXT DEFAULT '',
            diagnosis TEXT DEFAULT '',
            difficulty TEXT NOT NULL DEFAULT 'medium',
            teaching_points JSONB DEFAULT '[]'::jsonb,
            differential_diagnosis JSONB DEFAULT '[]'::jsonb,
            annotations JSONB DEFAULT '[]'::jsonb,
            findings_text TEXT DEFAULT '',
            submitted_by TEXT DEFAULT '',
            tenant_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_teaching_files_modality
        ON teaching_files(modality)
        """)

    async def create(self, data):
        await self.sync_db()
        import json as _json
        row = await self.conn.fetchrow(
            """INSERT INTO teaching_files
               (exam_id, title, modality, body_part, diagnosis, difficulty,
                teaching_points, differential_diagnosis, annotations,
                findings_text, submitted_by, tenant_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb,
                       $9::jsonb, $10, $11, $12)
               RETURNING *""",
            data.get('exam_id'), data.get('title') or '',
            data.get('modality') or '', data.get('body_part') or '',
            data.get('diagnosis') or '', data.get('difficulty') or 'medium',
            _json.dumps(data.get('teaching_points') or []),
            _json.dumps(data.get('differential_diagnosis') or []),
            _json.dumps(data.get('annotations') or []),
            data.get('findings_text') or '',
            str(data.get('submitted_by') or ''),
            data.get('tenant_id'),
        )
        return dict(row) if row else None

    async def get(self, tf_id):
        await self.sync_db()
        row = await self.conn.fetchrow(
            "SELECT * FROM teaching_files WHERE id::text = $1", str(tf_id),
        )
        return dict(row) if row else None

    async def list_files(self, modality=None, body_part=None, diagnosis=None,
                         difficulty=None, limit=50, offset=0):
        """Browse the library — newest first, filterable on the axes the
        resident curriculum filters on."""
        await self.sync_db()
        where, params = ['TRUE'], []
        if modality:
            params.append(modality)
            where.append(f"modality = ${len(params)}")
        if body_part:
            params.append(body_part)
            where.append(f"body_part = ${len(params)}")
        if diagnosis:
            params.append(f'%{diagnosis}%')
            where.append(f"diagnosis ILIKE ${len(params)}")
        if difficulty:
            params.append(difficulty)
            where.append(f"difficulty = ${len(params)}")
        rows = await self.conn.fetch(
            f"""SELECT * FROM teaching_files
                WHERE {' AND '.join(where)}
                ORDER BY created_at DESC
                LIMIT {int(limit)} OFFSET {int(offset)}""",
            *params,
        )
        return [dict(r) for r in rows]
