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
        # technologist review P1-1: critical-results flag (CRITICAL_RESULTS_WRITE)
        # lets a technologist mark an alarming finding during acquisition so the
        # radiologist reads it out of order. ALTER-style guards keep idempotent.
        await self.exec("""
        ALTER TABLE exams ADD COLUMN IF NOT EXISTS critical_flag TEXT DEFAULT ''
        """)
        await self.exec("""
        ALTER TABLE exams ADD COLUMN IF NOT EXISTS critical_flag_note TEXT DEFAULT ''
        """)
        await self.exec("""
        ALTER TABLE exams ADD COLUMN IF NOT EXISTS critical_flagged_at TIMESTAMPTZ
        """)
        await self.exec("""
        ALTER TABLE exams ADD COLUMN IF NOT EXISTS critical_flagged_by TEXT DEFAULT ''
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
                                    priority=None, search=None, assigned=None):
        """Exams for a technologist's worklist (technologist review P1-2).

        By default the list is the assignment union: exams assigned to this
        technologist PLUS the unassigned pool (assigned_technologist = ''),
        which every technologist sees so nobody misses a STAT. `assigned`
        narrows that: 'mine' -> only this technologist's rows, 'pool' -> only
        the unassigned ones, so the UI can label ownership honestly.

        F1: the list is row-level tenant-scoped (role-walk technologist).
        Shared-DB tenants (uses_main_database) share one pool AND one table,
        so pool-level isolation is not enough — without this filter an acme
        technologist sees every other tenant's exams.
        """
        from pypika import Query as PypikaQuery

        tenant = get_tenant_slug() or 'default'
        assigned_me = self.table.assigned_technologist == username
        unassigned = self.table.assigned_technologist == ''
        conditions = [self.table.tenant_id == tenant]
        if assigned == 'mine':
            conditions.append(assigned_me)
        elif assigned == 'pool':
            conditions.append(unassigned)
        else:
            conditions.append(assigned_me | unassigned)
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
        # technologist review P1-3: the Completed tab shows the read state of
        # the tech's handoffs (reports.status: draft -> preliminary ->
        # submitted -> final), so the worklist carries it without a second
        # request per row.
        q = PypikaQuery.from_(self.table).select(self.table.star)
        for c in conditions:
            q = q.where(c)
        rows = await self.fetch(q)
        items = [dict(r) for r in rows]
        if items:
            ids = [r['id'] for r in items]
            report_rows = await self.conn.fetch(
                "SELECT exam_id, status FROM reports WHERE exam_id = ANY($1::uuid[])",
                ids,
            )
            status_by_exam = {r['exam_id']: r['status'] for r in report_rows}
            for r in items:
                r['report_status'] = status_by_exam.get(r['id'])
        items.sort(key=lambda r: (
            priority_order.get(r.get('priority', 'routine'), 9),
            -(r.get('created_at') or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
        ))
        return items

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
        # T-06: clinical indication text + per-user favorites.
        await self.exec("""
        ALTER TABLE protocols
        ADD COLUMN IF NOT EXISTS clinical_indication TEXT NOT NULL DEFAULT ''
        """)
        await self.exec("""
        CREATE TABLE IF NOT EXISTS protocol_favorites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            protocol_id UUID NOT NULL REFERENCES protocols(id) ON DELETE CASCADE,
            tenant_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_protocol_favorites UNIQUE (user_id, protocol_id)
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_protocol_favorites_user
        ON protocol_favorites(user_id)
        """)

    async def list_by_modality(self, modality=None, body_part=None, q=None,
                               user_id=None):
        """List protocols with optional filters and a per-user favorite flag.

        T-06: body_part/q narrow the registry (q matches name, body part or
        clinical indication); user_id LEFT JOINs protocol_favorites so rows
        carry `is_favorite` for the console star toggle."""
        clauses, args = [], []
        if modality:
            args.append(modality)
            clauses.append(f"p.modality = ${len(args)}")
        if body_part:
            args.append(body_part)
            clauses.append(f"p.body_part = ${len(args)}")
        if q:
            args.append(f"%{q}%")
            i = len(args)
            clauses.append(
                f"(p.name ILIKE ${i} OR p.body_part ILIKE ${i}"
                f" OR p.clinical_indication ILIKE ${i})"
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        fav = ''
        if user_id:
            args.append(str(user_id))
            fav = (
                f"LEFT JOIN protocol_favorites pf"
                f" ON pf.protocol_id = p.id AND pf.user_id = ${len(args)}"
            )
        rows = await self.conn.fetch(
            f"""SELECT p.*, {'pf.id IS NOT NULL AS is_favorite'
                            if user_id else 'FALSE AS is_favorite'}
                FROM protocols p {fav} {where}
                ORDER BY p.modality, p.name""",
            *args,
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

    async def toggle_favorite(self, user_id, protocol_id, tenant=None):
        """T-06: flip the user's favorite flag; True=now favorite."""
        deleted = await self.conn.fetchval(
            """DELETE FROM protocol_favorites
               WHERE user_id = $1 AND protocol_id = $2 RETURNING id""",
            str(user_id), str(protocol_id),
        )
        if deleted:
            return False
        await self.conn.execute(
            """INSERT INTO protocol_favorites (user_id, protocol_id, tenant_id)
               VALUES ($1, $2, $3)""",
            str(user_id), str(protocol_id), tenant,
        )
        return True
