"""Add tenant_id discriminator to clinical data-plane tables

Revision ID: 057
Revises: 056
Create Date: 2026-08-12

Why
---
Only `files` carried a tenant discriminator (G-2 / F-1). The clinical tables
that the DICOM ingest and RIS workflows write into — patients, studies,
series, exams (+ acquisitions, safety_checks, incidents, protocol_overrides,
protocols) and worklist_entries — had no tenant_id. On a separate-DB tenant
deployment each tenant DB holds only that tenant's rows, so isolation holds at
the connection level; but the platform/main store (and any future row-level
backstop) needs a per-row discriminator so the `default` tenant's rows can be
distinctly tagged and so a tenant row can never be silently attributed to the
wrong scope. This closes the discriminator gap left open by F-1.

Data Migration
--------------
Adds a nullable tenant_id TEXT column + index to the tables above and
backfills existing rows to 'default' (the seeded platform tenant). On a
separate-DB tenant database the tables are provisioned empty, so the backfill
is a no-op there; tenant DBs get their correct slug on every new insert via
get_tenant_slug().

Rollback
--------
Drops the indexes and columns.

References
----------
- G-2 / F-1: only `files` had a tenant discriminator
"""

from alembic import op

revision = '057'
down_revision = '056'
branch_labels = None
depends_on = None

_TABLES = [
    'patients',
    'studies',
    'series',
    'exams',
    'acquisitions',
    'safety_checks',
    'incidents',
    'protocol_overrides',
    'protocols',
    'worklist_entries',
]


def upgrade():
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id TEXT"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant ON {table}(tenant_id)"
        )
        # Legacy rows belong to the seeded platform tenant.
        op.execute(
            f"UPDATE {table} SET tenant_id = 'default' WHERE tenant_id IS NULL"
        )


def downgrade():
    for table in _TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_tenant")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")
