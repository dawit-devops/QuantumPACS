"""RIS Report Templates DB layer (S8-06, S8-07).

Provides CRUD operations and seeding for standard radiologist reporting templates.
"""
from datetime import datetime, timezone
from db.table import Table

DEFAULT_TEMPLATES = [
    {
        'name': 'CT Head — Routine', 'modality': 'CT', 'body_part': 'Head',
        'findings_template': (
            'Technique: Non-contrast head CT.\n'
            'Ventricles: Normal size and position.\n'
            'Midline: No shift.\n'
            'Parenchyma: No acute intracranial hemorrhage, mass, or infarct.'
        ),
        'impression_template': 'No acute intracranial abnormality.',
        'is_default': True,
    },
    {
        'name': 'CT Chest — Routine', 'modality': 'CT', 'body_part': 'Chest',
        'findings_template': (
            'Technique: Contrast-enhanced chest CT.\n'
            'Lungs: No nodules, consolidation, or effusion.\n'
            'Mediastinum: No lymphadenopathy or mass.\n'
            'Pleura: Clear.'
        ),
        'impression_template': 'No acute cardiopulmonary abnormality.',
        'is_default': False,
    },
    {
        'name': 'CT Abdomen/Pelvis', 'modality': 'CT', 'body_part': 'Abdomen',
        'findings_template': (
            'Technique: IV and oral contrast CT abdomen/pelvis.\n'
            'Liver/Gallbladder: Unremarkable.\n'
            'Pancreas/Spleen: Normal.\n'
            'Bowel: No dilatation or wall thickening.\n'
            'Free fluid: None.'
        ),
        'impression_template': 'No acute intra-abdominal process.',
        'is_default': False,
    },
    {
        'name': 'MRI Brain — Routine', 'modality': 'MR', 'body_part': 'Brain',
        'findings_template': (
            'Technique: Multiplanar brain MRI (T1, T2, FLAIR, DWI).\n'
            'Parenchyma: No acute infarct, mass, or demyelinating lesion.\n'
            'Ventricles: Normal.\n'
            'Vascular: No acute occlusion.'
        ),
        'impression_template': 'No acute intracranial abnormality.',
        'is_default': True,
    },
    {
        'name': 'MRI Spine Lumbar', 'modality': 'MR', 'body_part': 'Spine',
        'findings_template': (
            'Technique: Multiplanar lumbar spine MRI.\n'
            'Alignment: Normal lordosis.\n'
            'Discs: Normal disc heights.\n'
            'Canal: No stenosis.'
        ),
        'impression_template': 'Unremarkable lumbar spine MRI.',
        'is_default': False,
    },
    {
        'name': 'DX Chest PA/LAT — Routine', 'modality': 'DX', 'body_part': 'Chest',
        'findings_template': (
            'Lungs: Clear, no focal opacity.\n'
            'Cardiac silhouette: Normal size.\n'
            'Bones: No acute fracture.'
        ),
        'impression_template': 'No acute cardiopulmonary abnormality.',
        'is_default': True,
    },
    {
        'name': 'DX Extremity — Fracture Check', 'modality': 'CR', 'body_part': 'Extremity',
        'findings_template': (
            'Bones: Normal alignment and bone density.\n'
            'Joints: Intact joint spaces.\n'
            'Soft tissues: Unremarkable.'
        ),
        'impression_template': 'No acute fracture or dislocation.',
        'is_default': True,
    },
    {
        'name': 'US Abdomen — Complete', 'modality': 'US', 'body_part': 'Abdomen',
        'findings_template': (
            'Liver: Normal echotexture, no mass.\n'
            'Gallbladder: No stones or wall thickening.\n'
            'Pancreas/Spleen/Kidneys: Unremarkable.\n'
            'No free fluid.'
        ),
        'impression_template': 'Normal abdominal ultrasound.',
        'is_default': True,
    },
    {
        'name': 'MG Mammogram 2D/3D', 'modality': 'MG', 'body_part': 'Breast',
        'findings_template': (
            'Breast density: Scattered fibroglandular density.\n'
            'Masses: None.\n'
            'Calcifications: No malignant type.'
        ),
        'impression_template': 'BI-RADS 1: Negative.',
        'is_default': True,
    },
    {
        'name': 'PET Whole Body — Routine', 'modality': 'PET', 'body_part': 'Whole Body',
        'findings_template': (
            'No abnormal FDG-avid focus to suggest malignancy.\n'
            'Physiologic distribution of tracer.'
        ),
        'impression_template': 'Negative whole-body PET.',
        'is_default': True,
    },
]


class RisReportTemplates(Table):
    name = 'ris_report_templates'

    async def sync_db(self):
        await self.exec("""
        CREATE TABLE IF NOT EXISTS ris_report_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            modality TEXT NOT NULL,
            body_part TEXT DEFAULT '',
            findings_template TEXT DEFAULT '',
            impression_template TEXT DEFAULT '',
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """)
        await self.exec("""
        CREATE INDEX IF NOT EXISTS ix_ris_templates_modality ON ris_report_templates(modality)
        """)

    async def list_templates(self, modality=None):
        """List report templates, optionally filtered by modality."""
        await self.sync_db()
        if modality:
            rows = await self.conn.fetch(
                "SELECT * FROM ris_report_templates WHERE UPPER(modality) = UPPER($1) ORDER BY name",
                modality,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM ris_report_templates ORDER BY modality, name"
            )
        return [dict(r) for r in rows]

    async def create_template(self, data):
        """Create a new report template."""
        await self.sync_db()
        now = datetime.now(timezone.utc)
        row = await self.conn.fetchrow(
            """INSERT INTO ris_report_templates
               (name, modality, body_part, findings_template, impression_template, is_default, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               RETURNING *""",
            data['name'], data['modality'], data.get('body_part', ''),
            data.get('findings_template', ''), data.get('impression_template', ''),
            data.get('is_default', False), now, now,
        )
        return dict(row) if row else None

    async def seed_defaults(self):
        """Seed initial 10 default templates idempotently."""
        await self.sync_db()
        count = await self.conn.fetchval("SELECT count(*) FROM ris_report_templates")
        if count and count > 0:
            return
        for t in DEFAULT_TEMPLATES:
            await self.create_template(t)

    # ------------------------------------------------------------------
    # R2-02-07/09: versioning — publish snapshots + one-click rollback.
    # ------------------------------------------------------------------

    async def list_versions(self, template_id, tenant_id='default'):
        """Version history for a template, newest first."""
        return await self.conn.fetch(
            "SELECT id, template_id, version_number, findings_template,"
            " impression_template, published_by, published_at"
            " FROM ris_report_template_versions"
            " WHERE template_id = $1 AND tenant_id = $2"
            " ORDER BY version_number DESC",
            template_id, tenant_id,
        )

    async def publish_version(self, template_id, *, findings,
                              impression, published_by='',
                              tenant_id='default'):
        """Snapshot the new body as the next version and activate it."""
        current = await self.conn.fetchrow(
            "SELECT COALESCE(MAX(version_number), 0) AS v"
            " FROM ris_report_template_versions"
            " WHERE template_id = $1 AND tenant_id = $2",
            template_id, tenant_id,
        )
        next_version = ((current or {}).get('v') or 0) + 1
        row = await self.conn.fetchrow(
            "INSERT INTO ris_report_template_versions"
            " (tenant_id, template_id, version_number,"
            "  findings_template, impression_template, published_by)"
            " VALUES ($1, $2, $3, $4, $5, $6)"
            " RETURNING id, template_id, version_number",
            tenant_id, template_id, next_version, findings, impression,
            str(published_by),
        )
        await self.conn.execute(
            "UPDATE ris_report_templates"
            " SET findings_template = $2, impression_template = $3,"
            " updated_at = now()"
            " WHERE id = $1 AND tenant_id = $4",
            template_id, findings, impression, tenant_id,
        )
        return row

    async def _get_version(self, template_id, version_number,
                           tenant_id='default'):
        return await self.conn.fetchrow(
            "SELECT id, template_id, version_number, findings_template,"
            " impression_template FROM ris_report_template_versions"
            " WHERE template_id = $1 AND version_number = $2"
            " AND tenant_id = $3",
            template_id, int(version_number), tenant_id,
        )

    async def apply_version(self, target):
        """Activate a prior version's body and snapshot it as a new
        rollback version so history records the undo itself."""
        row = await self.publish_version(
            target['template_id'],
            findings=target['findings_template'],
            impression=target['impression_template'],
            published_by='rollback',
        )
        await self.conn.execute(
            "UPDATE ris_report_templates"
            " SET findings_template = $2, impression_template = $3,"
            " updated_at = now()"
            " WHERE id = $1",
            target['template_id'], target['findings_template'],
            target['impression_template'],
        )
        return row

    async def rollback_to_version(self, template_id, version_number,
                                  actor='', tenant_id='default'):
        """Re-activate an older version. Returns None when unknown."""
        target = await self._get_version(
            template_id, version_number, tenant_id)
        if not target:
            return None
        return await self.apply_version(target)
