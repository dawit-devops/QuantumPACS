"""Add tenant column to files (HI-2: dead cross-tenant guard)

Revision ID: 050
Revises: 049
Create Date: 2026-08-10

Why
---
HI-2 (round-2 audit): `api/files.py` `_outside_effective_tenant` reads
`file.get('tenant')`, but the files table had no tenant column, so the guard
always returned False — a dead existence-oracle. Every file row must carry
the slug of the tenant whose data store owns it so the guard can refuse
files outside the request's effective scope (and the ES indexer can scope
documents, CR-1).

Schema
------
Adds `files.tenant TEXT` (nullable — platform/main-store rows stay NULL),
backfills main-store rows to 'default' when the seeded default tenant row
exists (fresh DBs may not have one), an FK to tenants(slug) and an index on
the new column. Tenant DBs get the same migration; their files tables are
empty at provision time, so the backfill is a no-op there.

Rollback
--------
Drops the FK, the index and the column. Backfilled values are not restored
(they were NULL before — revert is lossless for new rows only).
"""

from alembic import op

revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE files ADD COLUMN IF NOT EXISTS tenant TEXT")
    # Backfill: rows already in the main store belong to the seeded default
    # tenant (whose data store IS the main database). Guarded by EXISTS —
    # a fresh DB without a 'default' registry row must not trip the FK.
    op.execute("""
    UPDATE files SET tenant = 'default'
    WHERE tenant IS NULL
      AND EXISTS (SELECT 1 FROM tenants WHERE slug = 'default')
    """)
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'fk_files_tenant'
        ) THEN
            ALTER TABLE files ADD CONSTRAINT fk_files_tenant
                FOREIGN KEY (tenant) REFERENCES tenants(slug);
        END IF;
    END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_files_tenant ON files(tenant)")


def downgrade():
    op.execute("ALTER TABLE files DROP CONSTRAINT IF EXISTS fk_files_tenant")
    op.execute("DROP INDEX IF EXISTS ix_files_tenant")
    op.execute("ALTER TABLE files DROP COLUMN IF EXISTS tenant")
