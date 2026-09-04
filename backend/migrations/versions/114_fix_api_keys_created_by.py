"""fix api_keys.created_by type to match integer users.id

Revision ID: 114
Revises: 113
Create Date: 2026-08-28

Why
---
The `users` table uses `id SERIAL PRIMARY KEY` (integer) but `api_keys.created_by`
was created as UUID in migration 016. Creating an API key from the UI/service
keys page stores the creator's integer user id, so the insert always fails with
`DatatypeMismatchError: column "created_by" is of type uuid but expression is of
type integer`. This breaks API-key creation for every role (super_admin,
tenant_admin, ...). The table is empty in practice, so no data cast is needed.

Rollback
--------
ALTER TABLE api_keys ALTER COLUMN created_by TYPE uuid USING NULL. Safe:
additive column-type correction on an effectively-empty table.
"""

import sqlalchemy as sa
from alembic import op

revision = '114'
down_revision = '113'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN created_by TYPE BIGINT USING NULL::bigint"
    )


def downgrade():
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN created_by TYPE UUID USING NULL::uuid"
    )
