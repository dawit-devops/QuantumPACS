"""Exam lifecycle tables for the R06 Technologist workflow.

Schema covers the full exam lifecycle (FR-R06-01..10):
- exams: one row per imaging exam, created from (or alongside) a worklist entry
- acquisitions: per-series image acquisition records with dose params (FR-R06-04/05)
- safety_checks: pre-contrast allergy/pregnancy confirmations (FR-R06-06)
- incidents: retake/incident logging (FR-R06-08)
- protocol_overrides: audited emergency overrides (FR-R06-09)
- protocols: modality protocol registry (FR-R06-03/10)
"""
from datetime import datetime, timezone

from db.conn import get_tenant_slug
from db.table import Table


class Exams(Table):
    name = 'exams'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS exams (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            worklist_entry_id UUID,
            patient_id TEXT NOT NULL,
            patient_name TEXT NOT NULL DEFAULT '',
            patient_birth_date TEXT DEFAULT '',
            patient_sex TEXT DEFAULT '',
            accession_number TEXT DEFAULT '',
            requested_procedure_desc TEXT DEFAULT '',
            modality TEXT DEFAULT '',
            station_ae_title TEXT DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'routine'
                CHECK (priority IN ('routine', 'urgent', 'stat')),
            protocol_name TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'ready'
                CHECK (status IN ('ready', 'in_progress', 'completed', 'cancelled')),
            assigned_technologist TEXT DEFAULT '',
            assigned_radiologist TEXT DEFAULT '',
            referring_physician TEXT DEFAULT '',
            identity_confirmed_at TIMESTAMPTZ,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_exams_status ON exams(status)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_exams_technologist ON exams(assigned_technologist)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_exams_accession ON exams(accession_number)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_exams_radiologist ON exams(assigned_radiologist)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_exams_tenant ON exams(tenant_id)
        """)

    async def create(self, data):
        now = datetime.now(timezone.utc)
        q = self.insert().columns(
            'worklist_entry_id', 'patient_id', 'patient_name', 'patient_birth_date',
            'patient_sex', 'accession_number', 'requested_procedure_desc', 'modality',
            'station_ae_title', 'priority', 'protocol_name', 'status',
            'assigned_technologist', 'assigned_radiologist', 'referring_physician',
            'created_by', 'created_at', 'updated_at', 'tenant_id',
        ).insert((
            data.get('worklist_entry_id'),
            data['patient_id'],
            data.get('patient_name', ''),
            data.get('patient_birth_date', ''),
            data.get('patient_sex', ''),
            data.get('accession_number', ''),
            data.get('requested_procedure_desc', ''),
            data.get('modality', ''),
            data.get('station_ae_title', ''),
            data.get('priority', 'routine'),
            data.get('protocol_name', ''),
            'ready',
            data.get('assigned_technologist', ''),
            data.get('assigned_radiologist', ''),
            data.get('referring_physician', ''),
            data.get('created_by', ''),
            now, now,
            get_tenant_slug() or 'default',
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create exam')
        exam_id = row['id']
        return await self.get(exam_id)

    async def assign_radiologist(self, exam_id, radiologist_id):
        """Claim an exam for a radiologist (per-physician reading worklist).

        Unassignment is an explicit empty string, so callers pass the value
        they want persisted rather than None.
        """
        await self.conn.execute(
            "UPDATE exams SET assigned_radiologist = $2, updated_at = now() "
            "WHERE id = $1",
            exam_id, radiologist_id,
        )
        return await self.get(exam_id)

    async def get(self, exam_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM exams WHERE id = $1", exam_id,
        )
        return dict(row) if row else None

    async def list_for_technologist(self, username, status=None, modality=None,
                                    priority=None, search=None):
        from pypika import Query as PypikaQuery

        conditions = [
            (self.table.assigned_technologist == username) |
            (self.table.assigned_technologist == ''),
        ]
        if status:
            conditions.append(self.table.status == status)
        if modality:
            conditions.append(self.table.modality == modality)
        if priority:
            conditions.append(self.table.priority == priority)
        if search:
            like = f'%{search}%'
            conditions.append(
                (self.table.patient_name.ilike(like)) |
                (self.table.patient_id.ilike(like)) |
                (self.table.accession_number.ilike(like))
            )

        # STAT first, then urgent, then routine; newest first within a tier.
        priority_order = {
            'stat': 0, 'urgent': 1, 'routine': 2,
        }
        q = PypikaQuery.from_(self.table).select(self.table.star)
        for c in conditions:
            q = q.where(c)
        rows = await self.fetch(q)
        rows = [dict(r) for r in rows]
        rows.sort(key=lambda r: (
            priority_order.get(r.get('priority', 'routine'), 9),
            -(r.get('created_at') or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
        ))
        return rows

    async def update_status(self, exam_id, status, **extra):
        now = datetime.now(timezone.utc)
        fields = ['status', 'updated_at']
        values = [status, now]
        for k, v in extra.items():
            fields.append(k)
            values.append(v)
        set_clause = ', '.join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        await self.conn.execute(
            f"UPDATE exams SET {set_clause} WHERE id = $1",
            exam_id, *values,
        )


class Acquisitions(Table):
    name = 'acquisitions'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS acquisitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            series_number INT NOT NULL DEFAULT 1,
            instance_uid TEXT DEFAULT '',
            description TEXT DEFAULT '',
            kvp FLOAT DEFAULT 0,
            mas FLOAT DEFAULT 0,
            dlp FLOAT DEFAULT 0,
            ctdivol FLOAT DEFAULT 0,
            exposure_time FLOAT DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'accepted', 'rejected')),
            reject_reason TEXT DEFAULT '',
            acquired_at TIMESTAMPTZ DEFAULT now(),
            created_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_acquisitions_exam ON acquisitions(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_acquisitions_tenant ON acquisitions(tenant_id)
        """)

    async def create(self, data):
        q = self.insert().columns(
            'exam_id', 'series_number', 'instance_uid', 'description', 'kvp',
            'mas', 'dlp', 'ctdivol', 'exposure_time', 'status', 'tenant_id',
        ).insert((
            data['exam_id'],
            data.get('series_number', 1),
            data.get('instance_uid', ''),
            data.get('description', ''),
            data.get('kvp', 0),
            data.get('mas', 0),
            data.get('dlp', 0),
            data.get('ctdivol', 0),
            data.get('exposure_time', 0),
            data.get('status', 'pending'),
            get_tenant_slug() or 'default',
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create acquisition')
        return await self.get(row['id'])

    async def get(self, acquisition_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM acquisitions WHERE id = $1", acquisition_id,
        )
        return dict(row) if row else None

    async def list_for_exam(self, exam_id):
        rows = await self.conn.fetch(
            "SELECT * FROM acquisitions WHERE exam_id = $1 ORDER BY series_number, acquired_at",
            exam_id,
        )
        return [dict(r) for r in rows]

    async def set_status(self, acquisition_id, status, reject_reason=''):
        await self.conn.execute(
            "UPDATE acquisitions SET status = $2, reject_reason = $3 WHERE id = $1",
            acquisition_id, status, reject_reason,
        )

    async def rejected_count(self, exam_id):
        return await self.conn.fetchval(
            "SELECT count(*) FROM acquisitions WHERE exam_id = $1 AND status = 'rejected'",
            exam_id,
        ) or 0

    async def dose_totals(self, exam_id):
        row = await self.conn.fetchrow(
            """SELECT
                 COALESCE(SUM(dlp), 0)::float AS total_dlp,
                 COALESCE(SUM(ctdivol), 0)::float AS total_ctdivol,
                 COALESCE(SUM(mas), 0)::float AS total_mas,
                 COALESCE(SUM(exposure_time), 0)::float AS total_exposure
               FROM acquisitions WHERE exam_id = $1""",
            exam_id,
        )
        return dict(row) if row else {}


class SafetyChecks(Table):
    name = 'safety_checks'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS safety_checks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            check_item TEXT NOT NULL,
            answer TEXT NOT NULL,
            notes TEXT DEFAULT '',
            checked_by TEXT DEFAULT '',
            checked_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_safety_checks_exam ON safety_checks(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_safety_checks_tenant ON safety_checks(tenant_id)
        """)

    async def create(self, data):
        q = self.insert().columns(
            'exam_id', 'check_item', 'answer', 'notes', 'checked_by', 'tenant_id',
        ).insert((
            data['exam_id'], data['check_item'], data['answer'],
            data.get('notes', ''), data.get('checked_by', ''),
            get_tenant_slug() or 'default',
        )).returning('id')
        row = await self.fetchone(q)
        return dict(row) if row else None

    async def list_for_exam(self, exam_id):
        rows = await self.conn.fetch(
            "SELECT * FROM safety_checks WHERE exam_id = $1 ORDER BY checked_at",
            exam_id,
        )
        return [dict(r) for r in rows]


class Incidents(Table):
    name = 'incidents'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS incidents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium'
                CHECK (severity IN ('low', 'medium', 'high', 'critical')),
            description TEXT NOT NULL,
            reported_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_incidents_exam ON incidents(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_incidents_tenant ON incidents(tenant_id)
        """)

    async def create(self, data):
        q = self.insert().columns(
            'exam_id', 'incident_type', 'severity', 'description', 'reported_by',
            'tenant_id',
        ).insert((
            data['exam_id'], data['incident_type'], data['severity'],
            data['description'], data.get('reported_by', ''),
            get_tenant_slug() or 'default',
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

    async def list_for_exam(self, exam_id):
        rows = await self.conn.fetch(
            "SELECT * FROM incidents WHERE exam_id = $1 ORDER BY created_at",
            exam_id,
        )
        return [dict(r) for r in rows]


class ProtocolOverrides(Table):
    name = 'protocol_overrides'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS protocol_overrides (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            exam_id UUID NOT NULL,
            justification TEXT NOT NULL,
            original_params JSONB DEFAULT '{}'::jsonb,
            overridden_params JSONB DEFAULT '{}'::jsonb,
            overridden_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_protocol_overrides_exam ON protocol_overrides(exam_id)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_protocol_overrides_tenant ON protocol_overrides(tenant_id)
        """)

    async def create(self, data):
        import json as _json
        q = self.insert().columns(
            'exam_id', 'justification', 'original_params', 'overridden_params',
            'overridden_by', 'tenant_id',
        ).insert((
            data['exam_id'], data['justification'],
            _json.dumps(data.get('original_params') or {}),
            _json.dumps(data.get('overridden_params') or {}),
            data.get('overridden_by', ''),
            get_tenant_slug() or 'default',
        )).returning('id')
        row = await self.fetchone(q)
        if not row:
            raise RuntimeError('Failed to create override')
        return await self.get(row['id'])

    async def get(self, override_id):
        row = await self.conn.fetchrow(
            "SELECT * FROM protocol_overrides WHERE id = $1", override_id,
        )
        return dict(row) if row else None

    async def list_for_exam(self, exam_id):
        rows = await self.conn.fetch(
            "SELECT * FROM protocol_overrides WHERE exam_id = $1 ORDER BY created_at",
            exam_id,
        )
        return [dict(r) for r in rows]


class Protocols(Table):
    name = 'protocols'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS protocols (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            modality TEXT NOT NULL,
            body_part TEXT DEFAULT '',
            sequences JSONB DEFAULT '[]'::jsonb,
            parameters JSONB DEFAULT '{}'::jsonb,
            acr_benchmark_dlp FLOAT,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            tenant_id TEXT
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_protocols_modality ON protocols(modality)
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_protocols_tenant ON protocols(tenant_id)
        """)

    async def list_by_modality(self, modality=None):
        if modality:
            rows = await self.conn.fetch(
                "SELECT * FROM protocols WHERE modality = $1 ORDER BY name",
                modality,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM protocols ORDER BY modality, name",
            )
        return [dict(r) for r in rows]

    async def get_default_for_modality(self, modality):
        row = await self.conn.fetchrow(
            """SELECT * FROM protocols
               WHERE modality = $1 AND (is_default OR TRUE)
               ORDER BY is_default DESC, name LIMIT 1""",
            modality,
        )
        return dict(row) if row else None
