"""Prep-checklist seeding arbiter (§2.11 N-02)

Revision ID: 101
Revises: 100
Create Date: 2026-08-26

Why
---
get_or_create seeded via SELECT-then-INSERT with no uniqueness backstop:
two concurrent console opens could both miss the probe and insert duplicate
checklist rows for one exam. Newest-first reads masked the duplicates, but a
confirm could land on a different physical row than the queue's newest —
marking a superseded checklist complete while the prep list still showed
work outstanding. A unique (exam_id, tenant_id) arbiter closes the race;
the dedupe keeps the newest row per pair so the index builds even on
databases that accumulated duplicates while seeding was unguarded.

Rollback drops the index; deduplicated rows stay deduplicated.
"""
from alembic import op

revision = '101'
down_revision = '100'
branch_labels = None
depends_on = None

# Keep exactly one row per (exam_id, tenant_id): delete `a` whenever a
# newer sibling exists, ties broken by id for identical timestamps.
_DEDUPE = """
DELETE FROM prep_checklists a
USING prep_checklists b
WHERE a.exam_id IS NOT NULL
  AND b.exam_id IS NOT NULL
  AND a.exam_id = b.exam_id
  AND a.tenant_id = b.tenant_id
  AND (b.created_at, b.id) > (a.created_at, a.id)
"""

_ARBITER = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_prep_checklists_exam_tenant "
    "ON prep_checklists(exam_id, tenant_id)"
)


def upgrade():
    # Dedupe must precede the arbiter or the unique index build fails on
    # databases that already hold duplicate seed rows.
    op.execute(_DEDUPE)
    op.execute(_ARBITER)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ux_prep_checklists_exam_tenant")
