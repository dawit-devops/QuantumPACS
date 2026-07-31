"""Add OAuth fields to users table

Revision ID: 009
Revises: 008
Create Date: 2026-07-25

Why
---
Adds OAuth/OpenID Connect fields (oauth_sub, email, avatar_url) to the users table
for linking external identity provider accounts.

Data Migration
--------------
None — new column additions only. Conditional partial index on oauth_sub.

Rollback
--------
Drops index and added columns.

References
----------
- ADR-009: OAuth integration design
"""

from alembic import op

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_sub TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT")
    op.execute("""
    CREATE INDEX IF NOT EXISTS users_oauth_sub ON users(oauth_sub)
    WHERE oauth_sub IS NOT NULL
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS users_oauth_sub")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar_url")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oauth_sub")
