"""Create per-user reading presets for the R12 staff radiologist workflow

Revision ID: 035
Revises: 034
Create Date: 2026-08-03

Why
---
Implements FR-R12-15 (reading presets): radiologists save window/level and
viewport-layout presets per modality and reuse them across sessions and
workstations. Presets are owned per user.

Tables
------
- reading_presets: one row per named preset (window_level | layout), owned by
  a user (users.id is bigint), keyed per modality with a unique name.

Data Migration
--------------
None — new table only.

Rollback
--------
Drops the table and its indexes.

References
----------
- docs/requirements/staff-radiologist/ (R12 package, FR-R12-15, US-R12-12)
"""

from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS reading_presets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id BIGINT NOT NULL,
        preset_type TEXT NOT NULL
            CHECK (preset_type IN ('window_level', 'layout')),
        modality TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL,
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        is_default BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_reading_presets_user_type_modality_name
        ON reading_presets(user_id, preset_type, modality, name)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_reading_presets_user
        ON reading_presets(user_id, preset_type, modality)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_reading_presets_user")
    op.execute("DROP INDEX IF EXISTS uq_reading_presets_user_type_modality_name")
    op.execute("DROP TABLE IF EXISTS reading_presets")
