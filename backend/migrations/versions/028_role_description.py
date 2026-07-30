"""Add description column to roles table

Revision ID: 028
Revises: 027
Create Date: 2026-07-29

Adds optional description field for human-readable role explanations.
"""

from alembic import op

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS description TEXT")


def downgrade():
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS description")
