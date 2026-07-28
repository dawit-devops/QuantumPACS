"""Add token_version to users for forced re-auth on role/permission changes

Revision ID: 024
Revises: 023
Create Date: 2026-07-28

Adds:
- users.token_version INTEGER DEFAULT 0
- Incremented on role change, permission change, deactivation
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0")


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS token_version")
