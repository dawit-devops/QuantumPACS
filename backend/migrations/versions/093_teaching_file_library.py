"""teaching file library

Revision ID: 093
Revises: 092
Create Date: 2026-08-24 21:30:00.000000

R-11/RES-03: curated teaching cases submitted from the reading console —
a completed exam plus the author's teaching points, differential diagnosis
and viewer annotations. Browsable by all reading roles.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '093'
down_revision: Union[str, None] = '092'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teaching_files_modality
        ON teaching_files(modality)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS teaching_files")
