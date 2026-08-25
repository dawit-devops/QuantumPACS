"""DB layer for the §2.11 nursing surfaces (N-01..N-04).

The 037 tables (`vitals`, `prep_checklists`) predate this module; migration
100 adds the missing weight/height columns, tenant tags and indexes. The two
new tables (`contrast_consents`, `exam_notes`) mirror that migration's DDL so
sync-only databases and migrated databases cannot diverge.

Self-heal contract (care_plans precedent): every entry point calls
`sync_db()` first, so databases provisioned without `alembic upgrade head`
still work — on migrated ones each statement is a no-op IF NOT EXISTS /
ADD COLUMN IF NOT EXISTS.

All rows are stamped with `tenant_id` following the encounters/care_plans
convention: pool isolation stays authoritative for tenant separation, the
tag keeps rows attributable in shared dev databases and analytics queries.
"""

from log import get_logger

log = get_logger(__name__)

# Spec §2.11 N-02: the interactive checklist's required items. Seeded on
# first access per exam; every required item must be checked before the
# checklist can be confirmed.
DEFAULT_CHECKLIST_ITEMS = [
    {'key': 'allergy_verification', 'label': 'Allergy verification', 'required': True},
    {'key': 'medication_review', 'label': 'Medication review', 'required': True},
    {'key': 'npo_status', 'label': 'NPO status verified', 'required': True},
    {'key': 'consent_form', 'label': 'Consent form on file', 'required': True},
    {'key': 'id_band_verified', 'label': 'ID band verified', 'required': True},
]

# Newest checklist per exam+tenant — shared by the seed probe and the
# lost-race read-back in get_or_create.
_NEWEST_CHECKLIST_SQL = """
    SELECT * FROM prep_checklists
    WHERE exam_id = $1 AND tenant_id = $2
    ORDER BY created_at DESC
    LIMIT 1
"""


class ExamVitals:
    """N-01 — timestamped vitals recorded before a procedure."""

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        # Mirror migration 100 for sync-created databases; idempotent on
        # migrated ones.
        await self.conn.execute(
            "ALTER TABLE vitals ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(5, 1)"
        )
        await self.conn.execute(
            "ALTER TABLE vitals ADD COLUMN IF NOT EXISTS height_cm NUMERIC(5, 1)"
        )
        await self.conn.execute(
            "ALTER TABLE vitals ADD COLUMN IF NOT EXISTS tenant_id "
            "TEXT NOT NULL DEFAULT 'default'"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_vitals_exam ON vitals(exam_id)"
        )

    async def record(self, *, exam_id, patient_id, bp_systolic=None,
                     bp_diastolic=None, heart_rate=None, spo2=None,
                     temperature_c=None, respiration=None, weight_kg=None,
                     height_cm=None, by='', tenant_id='default'):
        await self.sync_db()
        return await self.conn.fetchrow(
            """
            INSERT INTO vitals (
                exam_id, patient_id, bp_systolic, bp_diastolic, hr, spo2,
                temperature, respiration, weight_kg, height_cm,
                operator_id, recorded_at, tenant_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    COALESCE(NULL, now()), $12)
            RETURNING *
            """,
            exam_id, patient_id, bp_systolic, bp_diastolic, heart_rate,
            spo2, temperature_c, respiration, weight_kg, height_cm,
            by, tenant_id,
        )

    async def list_for_exam(self, exam_id, tenant_id='default', limit=50):
        await self.sync_db()
        return await self.conn.fetch(
            """
            SELECT * FROM vitals
            WHERE exam_id = $1 AND tenant_id = $2
            ORDER BY recorded_at DESC
            LIMIT $3
            """,
            exam_id, tenant_id, limit,
        )


class PrepChecklists:
    """N-02 — pre-procedure checklist; defaults seeded on first access."""

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _decode_items(row):
        """asyncpg returns jsonb as a raw string unless a codec is set —
        decode so handlers/clients always see a list."""
        if row and isinstance(row.get('items'), str):
            import json

            return dict(row, items=json.loads(row['items']))
        return row

    @staticmethod
    def _union_defaults(row):
        """Spec evolution: items added to DEFAULT_CHECKLIST_ITEMS must reach
        exams whose checklist row predates them — append any default keys
        missing from the stored catalog so a newly required item shows in
        the UI and blocks confirmation."""
        if not row:
            return row
        stored = row.get('items') or []
        keys = {i.get('key') for i in stored}
        extra = [
            {**d, 'checked': False}
            for d in DEFAULT_CHECKLIST_ITEMS if d['key'] not in keys
        ]
        if not extra:
            return row
        return dict(row, items=list(stored) + extra)

    async def sync_db(self):
        # The unique seeding arbiter arrives via migration 101 only — it
        # needs a dedupe pass first, which is data work this idempotent
        # DDL path must not repeat per call. On sync-only databases the
        # target-less ON CONFLICT below degrades safely instead.
        await self.conn.execute(
            "ALTER TABLE prep_checklists ADD COLUMN IF NOT EXISTS tenant_id "
            "TEXT NOT NULL DEFAULT 'default'"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_prep_checklists_exam "
            "ON prep_checklists(exam_id)"
        )

    async def get_or_create(self, *, exam_id, patient_id,
                            procedure_type='', tenant_id='default'):
        await self.sync_db()
        row = await self.conn.fetchrow(
            _NEWEST_CHECKLIST_SQL, exam_id, tenant_id,
        )
        if row:
            return self._union_defaults(self._decode_items(row))
        import json

        # Target-less ON CONFLICT DO NOTHING: on migrated databases the
        # migration-101 unique index makes concurrent seeds race-safe (the
        # loser falls through to a read-back of the winner); on sync-only
        # databases without that index it is a plain insert, never an error.
        inserted = await self.conn.fetchrow(
            """
            INSERT INTO prep_checklists (
                exam_id, patient_id, procedure_type, items, status, tenant_id
            )
            VALUES ($1, $2, $3, $4::jsonb, 'in_progress', $5)
            ON CONFLICT DO NOTHING
            RETURNING *
            """,
            exam_id, patient_id, procedure_type,
            json.dumps(DEFAULT_CHECKLIST_ITEMS), tenant_id,
        )
        if inserted:
            return self._decode_items(inserted)
        return self._union_defaults(self._decode_items(
            await self.conn.fetchrow(_NEWEST_CHECKLIST_SQL, exam_id, tenant_id)
        ))

    async def confirm(self, checklist_id, by=''):
        """Mark complete + attribute. The API layer enforces the
        all-required-items-checked rule before calling this."""
        return self._decode_items(await self.conn.fetchrow(
            """
            UPDATE prep_checklists
            SET status = 'complete', confirmed_by = $2, confirmed_at = now(),
                updated_at = now()
            WHERE id = $1
            RETURNING *
            """,
            checklist_id, by,
        ))

    async def update_items(self, checklist_id, items):
        """Persist intermediate checkbox progress without confirming."""
        import json

        return self._decode_items(await self.conn.fetchrow(
            """
            UPDATE prep_checklists
            SET items = $2::jsonb, updated_at = now()
            WHERE id = $1
            RETURNING *
            """,
            checklist_id, json.dumps(items),
        ))


# Hoisted so tests can prepare (parse+plan) it against the live schema —
# the fake-conn harness pins the text, only Postgres catches bad casts,
# missing columns and SRF-over-NULL mistakes.
PREP_LIST_SQL = """
    SELECT e.id AS exam_id, e.patient_id, e.patient_name,
           e.modality, e.priority, e.status,
           p.id AS checklist_id,
           p.status AS checklist_status,
           COALESCE((
               SELECT COUNT(1) FROM jsonb_array_elements(p.items) it
               WHERE (it->>'checked')::boolean
           ), 0) AS checked_count,
           COALESCE((
               SELECT COUNT(1) FROM jsonb_array_elements(p.items) it
               WHERE (it->>'required')::boolean
           ), 0) AS required_count
    FROM exams e
    LEFT JOIN LATERAL (
        SELECT pc.id, pc.status, pc.items
        FROM prep_checklists pc
        WHERE pc.exam_id = e.id AND pc.tenant_id = $1
        ORDER BY pc.created_at DESC
        LIMIT 1
    ) p ON TRUE
    WHERE e.status IN ('ready', 'in_progress')
    ORDER BY e.created_at DESC
    LIMIT $2
"""


class NursingPrepList:
    """Today's exams awaiting nursing prep with their checklist state.

    A thin read over the existing `exams` rows — deliberately NOT a second
    worklist model: one row per ready/in-progress exam, LEFT JOINed to the
    newest checklist so the queue shows what still needs prepping.
    """

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_exams_status ON exams(status)"
        )

    async def list(self, tenant_id='default', limit=100):
        await self.sync_db()
        return await self.conn.fetch(PREP_LIST_SQL, tenant_id, limit)


class ContrastConsents:
    """N-03 — digital contrast consent with signature capture."""

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contrast_consents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                exam_id UUID,
                patient_id TEXT NOT NULL,
                consent_text_version TEXT DEFAULT '',
                accepted BOOLEAN NOT NULL DEFAULT TRUE,
                signature_png TEXT DEFAULT '',
                declined_reason TEXT DEFAULT '',
                witnessed_by TEXT DEFAULT '',
                signed_by TEXT DEFAULT '',
                signed_at TIMESTAMPTZ DEFAULT now(),
                created_at TIMESTAMPTZ DEFAULT now(),
                tenant_id TEXT NOT NULL DEFAULT 'default'
            )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_contrast_consents_exam "
            "ON contrast_consents(tenant_id, exam_id, signed_at DESC)"
        )

    async def create(self, *, exam_id, patient_id, accepted=True,
                     signature_png='', declined_reason='',
                     consent_text_version='', witnessed_by='', by='',
                     tenant_id='default'):
        await self.sync_db()
        # Both reads of this table project explicit columns excluding
        # signature_png: up to ~280 KB of base64 that no consumer renders
        # (the panel shows decision/timestamp only). Fetch it explicitly if
        # a signature viewer is ever built.
        return await self.conn.fetchrow(
            """
            INSERT INTO contrast_consents (
                exam_id, patient_id, accepted, signature_png,
                declined_reason, consent_text_version, witnessed_by,
                signed_by, signed_at, tenant_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now(), $9)
            RETURNING id, exam_id, patient_id, accepted, declined_reason,
                      consent_text_version, witnessed_by, signed_by,
                      signed_at, created_at, tenant_id
            """,
            exam_id, patient_id, accepted, signature_png, declined_reason,
            consent_text_version, witnessed_by, by, tenant_id,
        )

    async def get_for_exam(self, exam_id, tenant_id='default'):
        await self.sync_db()
        return await self.conn.fetchrow(
            """
            SELECT id, exam_id, patient_id, accepted, declined_reason,
                   consent_text_version, witnessed_by, signed_by,
                   signed_at, created_at, tenant_id
            FROM contrast_consents
            WHERE exam_id = $1 AND tenant_id = $2
            ORDER BY signed_at DESC
            LIMIT 1
            """,
            exam_id, tenant_id,
        )


class ExamNotes:
    """N-04 — attributed free-text notes on an exam, visible to tech +
    radiologist via the any-of [NURSING_READ, EXAM_READ] read gate."""

    def __init__(self, conn):
        self.conn = conn

    async def sync_db(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS exam_notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                exam_id UUID,
                patient_id TEXT NOT NULL,
                note TEXT NOT NULL,
                author_id TEXT DEFAULT '',
                author_role TEXT DEFAULT 'nurse',
                created_at TIMESTAMPTZ DEFAULT now(),
                tenant_id TEXT NOT NULL DEFAULT 'default'
            )
        """)
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_exam_notes_exam "
            "ON exam_notes(tenant_id, exam_id, created_at DESC)"
        )

    async def add(self, *, exam_id, patient_id, note, author_id='',
                  author_role='nurse', tenant_id='default'):
        await self.sync_db()
        return await self.conn.fetchrow(
            """
            INSERT INTO exam_notes (
                exam_id, patient_id, note, author_id, author_role, tenant_id
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            exam_id, patient_id, note, author_id, author_role, tenant_id,
        )

    async def list_for_exam(self, exam_id, tenant_id='default', limit=100):
        await self.sync_db()
        return await self.conn.fetch(
            """
            SELECT * FROM exam_notes
            WHERE exam_id = $1 AND tenant_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            exam_id, tenant_id, limit,
        )
