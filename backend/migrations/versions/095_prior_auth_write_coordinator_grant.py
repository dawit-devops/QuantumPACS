"""prior-auth write grant for care_coordinator (G2)

Revision ID: 095
Revises: 094
Create Date: 2026-08-25 01:00:00.000000

G2 (human-approved 2026-08-25): PRIOR_AUTH_WRITE was held by no staff
built-in role — only super_admin passed its gates. It protects the P0
prior-auth management surface (create / submit-for-review / decide /
override, api/prior_auth.py) plus reminder send+config (api/reminders.py).
care_coordinator is the spec'd owner of both workflows (§2.7 CC-11/CC-12).

Additive jsonb append following migration 063's pattern; facility edits to
other grants are preserved.
"""

from alembic import op

revision = '095'
down_revision = '094'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE roles
        SET permissions = permissions || '["PRIOR_AUTH_WRITE"]'::jsonb,
            updated_at = now()
        WHERE slug = 'care_coordinator' AND built_in = TRUE
          AND NOT permissions ? 'PRIOR_AUTH_WRITE'
    """)


def downgrade():
    # Grant repair is a data change, not a schema inversion — nothing to undo.
    pass
