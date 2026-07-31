"""Add email and last_login to users table for account profile feature

Revision ID: 026
Revises: 025
Create Date: 2026-07-29

Adds:
- users.email VARCHAR(255) DEFAULT ''
- users.last_login TIMESTAMP
"""

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) DEFAULT ''")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_login")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email")
