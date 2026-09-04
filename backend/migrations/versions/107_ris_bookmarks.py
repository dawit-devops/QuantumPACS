"""Study bookmarks and collections tables — R-08.

Revision ID: 107
Revises: 106
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md R-08) needs study bookmarks
and collections for teaching, research, and follow-up. Two tables:
bookmark_collections (per-user named collections) and study_bookmarks
(study references bound to a user + optional collection).

Rollback
--------
DROP TABLE study_bookmarks, bookmark_collections. Safe: no production
data (feature not shipped).
"""

from alembic import op

revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade():
    # CREATE TABLE IF NOT EXISTS — the repo's sync_db() may have created the
    # tables already on a drifted dev database; keep this idempotent.
    op.execute("""
        CREATE TABLE IF NOT EXISTS bookmark_collections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_shared BOOLEAN NOT NULL DEFAULT FALSE,
            created_by TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bookmark_collections_user "
        "ON bookmark_collections(tenant_id, user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS study_bookmarks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT NOT NULL DEFAULT 'default',
            user_id TEXT NOT NULL,
            study_uid TEXT NOT NULL,
            study_desc TEXT DEFAULT '',
            collection_id TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_study_bookmarks_user "
        "ON study_bookmarks(tenant_id, user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_study_bookmarks_study "
        "ON study_bookmarks(study_uid)")


def downgrade():
    op.drop_table('study_bookmarks')
    op.drop_table('bookmark_collections')