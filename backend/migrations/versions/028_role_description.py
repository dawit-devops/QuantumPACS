"""Add description column to roles table

Revision ID: 028
Revises: 027
Create Date: 2026-07-29

Why
---
Adds optional description field to the roles table for human-readable role
explanations, making the admin UI role management more informative.

Data Migration
--------------
None — new column only.

Rollback
--------
Drops the description column.

References
----------
- RBAC feature: role description in admin UI
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
