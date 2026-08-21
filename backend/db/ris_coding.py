"""RIS Coding DB Layer (S11-02).

Maps procedure descriptions to CPT codes and clinical indications to ICD-10
codes using the seedable ris_coding_map table. The MVP uses a static seed
map (ROADMAP-v3.md: auto-coding deferred), with the API supporting manual
override. Code suggestions are per-procedure; a single procedure may map to
one CPT line (multi-line charge capture is a v1.1 concern).
"""

from db.table import Table

DEFAULT_SEED = [
    # (procedure_code, procedure_desc, cpt_code, cpt_description, icd10_code, icd10_description)
    ('CT CHEST', 'CT chest', '71250', 'CT chest without contrast',
     'R91.1', 'Lung opacity, unspecified'),
    ('CT ABDOMEN', 'CT abdomen', '74150', 'CT abdomen without contrast',
     'R10.9', 'Unspecified abdominal pain'),
    ('CT HEAD', 'CT head', '70450', 'CT head without contrast',
     'R51', 'Headache'),
    ('CT PELVIS', 'CT pelvis', '72192', 'CT pelvis without contrast',
     'R10.2', 'Pelvic and perineal pain'),
    ('MRI BRAIN', 'MRI brain', '70551', 'MRI brain without contrast',
     'G40.909', 'Unspecified epilepsy'),
    ('MRI LUMBAR', 'MRI lumbar spine', '72148', 'MRI lumbar spine without contrast',
     'M54.5', 'Low back pain'),
    ('US ABDOMEN', 'Ultrasound abdomen', '76700', 'US abdomen complete',
     'R10.9', 'Unspecified abdominal pain'),
    ('US PELVIS', 'Ultrasound pelvis', '76856', 'US pelvis complete',
     'N93.9', 'Abnormal uterine bleeding'),
    ('XRAY CHEST', 'X-ray chest', '71020', 'Radiologic exam chest 2 views',
     'R06.02', 'Shortness of breath'),
    ('XRAY ANKLE', 'X-ray ankle', '73600', 'Radiologic exam ankle 2 views',
     'S93.4', 'Ankle sprain'),
    ('PET CT', 'PET/CT', '78815', 'PET/CT tumor imaging',
     'C80.1', 'Malignant neoplasm without specification of site'),
    ('MAMMOGRAM', 'Screening mammography', '77067', 'Screening mammography bilateral',
     'Z12.31', 'Encounter for screening mammogram'),
]


class CodingService(Table):
    """Query ris_coding_map for CPT/ICD-10 suggestions."""

    name = 'ris_coding_map'

    async def sync_db(self):
        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ris_coding_map (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT DEFAULT 'default',
            procedure_code TEXT NOT NULL,
            procedure_desc TEXT DEFAULT '',
            cpt_code TEXT DEFAULT '',
            cpt_description TEXT DEFAULT '',
            icd10_code TEXT DEFAULT '',
            icd10_description TEXT DEFAULT '',
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (tenant_id, procedure_code)
        )
        """)

    async def seed_defaults(self, tenant_id='default'):
        """Insert the MVP seed map idempotently (NOT EXISTS per procedure)."""
        for row in DEFAULT_SEED:
            await self.conn.execute("""
            INSERT INTO ris_coding_map
                (tenant_id, procedure_code, procedure_desc, cpt_code,
                 cpt_description, icd10_code, icd10_description, active)
            SELECT $1, $2, $3, $4, $5, $6, $7, true
            WHERE NOT EXISTS (
                SELECT 1 FROM ris_coding_map
                WHERE tenant_id = $1 AND procedure_code = $2
            )
            """, tenant_id, *row)

    async def suggest_cpt(self, procedure_desc, tenant_id='default'):
        """Best CPT suggestion for a free-text procedure description.

        Matches on the seeded procedure_code key after uppercasing the query;
        returns {} when nothing matches so callers fall back to manual entry.
        """
        key = (procedure_desc or '').strip().upper()
        if not key:
            return {}
        rows = await self.conn.fetch(
            "SELECT procedure_code, cpt_code, cpt_description, icd10_code,"
            " icd10_description"
            " FROM ris_coding_map"
            " WHERE tenant_id = $1 AND active AND $2 ILIKE '%' || procedure_code || '%'"
            " ORDER BY procedure_code LIMIT 1",
            tenant_id, key,
        )
        return dict(rows[0]) if rows else {}

    async def suggest_icd10(self, indication, tenant_id='default'):
        """Best ICD-10 suggestion for a clinical indication."""
        if not (indication or '').strip():
            return {}
        rows = await self.conn.fetch(
            "SELECT procedure_code, cpt_code, icd10_code, icd10_description"
            " FROM ris_coding_map"
            " WHERE tenant_id = $1 AND active"
            " AND ($2 ILIKE '%' || icd10_description || '%'"
            "      OR icd10_description ILIKE '%' || $2 || '%')"
            " ORDER BY procedure_code LIMIT 1",
            tenant_id, (indication or '').strip(),
        )
        return dict(rows[0]) if rows else {}

    async def get_suggestions(self, procedure_desc, tenant_id='default'):
        """CPT + ICD-10 suggestion pair for a procedure (S11-06)."""
        cpt = await self.suggest_cpt(procedure_desc, tenant_id)
        if not cpt:
            return {}
        return {
            'procedure_code': cpt.get('procedure_code', ''),
            'cpt_code': cpt.get('cpt_code', ''),
            'cpt_description': cpt.get('cpt_description', ''),
            'icd10_code': cpt.get('icd10_code', ''),
            'icd10_description': cpt.get('icd10_description', ''),
        }
