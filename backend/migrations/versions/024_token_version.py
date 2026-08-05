"""Add token_version to users for forced re-auth on role/permission changes

Revision ID: 024
Revises: 023
Create Date: 2026-07-28

Why
---
Adds token_version to users — incremented on role change, permission change,
or deactivation to force existing JWT tokens to be rejected and require re-auth.

Data Migration
--------------
None — new column with DEFAULT 0.

Rollback
--------
Drops the token_version column.

References
----------
- ADR-024: Token invalidation on permission changes
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
