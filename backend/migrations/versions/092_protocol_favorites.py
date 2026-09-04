"""protocol favorites + clinical indication

Revision ID: 092
Revises: 091
Create Date: 2026-08-24 17:45:00.000000

T-06 (technologist G-04): per-user protocol favorites plus a searchable
clinical_indication text on the registry. Favorites live in their own table
(UNIQUE user_id + protocol_id, cascade on protocol delete); the column is a
plain ADD COLUMN IF NOT EXISTS so re-runs stay idempotent.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '092'
down_revision: Union[str, None] = '091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE protocols
        ADD COLUMN IF NOT EXISTS clinical_indication TEXT NOT NULL DEFAULT ''
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS protocol_favorites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            protocol_id UUID NOT NULL REFERENCES protocols(id)
                ON DELETE CASCADE,
            tenant_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_protocol_favorites UNIQUE (user_id, protocol_id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_protocol_favorites_user
        ON protocol_favorites(user_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS protocol_favorites")
    op.execute(
        "ALTER TABLE protocols DROP COLUMN IF EXISTS clinical_indication"
    )
