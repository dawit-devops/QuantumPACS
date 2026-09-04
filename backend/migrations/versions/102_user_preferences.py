"""Per-user preference documents (§3 configurable-widget substrate)

Revision ID: 102
Revises: 101
Create Date: 2026-08-26

Why
---
The UI/UX spec's configurable widget dashboards persist per-user layouts
(`dashboard_layout`), and no generic user-preferences storage exists. A
single JSONB document column on `users` serves every future per-user
preference without a table per feature; top-level keys are merged by the
write path so independent features never clobber each other's section.

Rollback is a deliberate no-op (mirrors migration 100's additive-column
rationale): the column carries no data until the feature ships and
dropping it would destroy saved user layouts.
"""
from alembic import op

revision = '102'
down_revision = '101'
branch_labels = None
depends_on = None

_DDL = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences "
    "JSONB NOT NULL DEFAULT '{}'::jsonb"
)


def upgrade():
    op.execute(_DDL)


def downgrade():
    # Documented no-op: additive column stays (see header).
    pass
