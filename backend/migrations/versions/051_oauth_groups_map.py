"""Add groups_map to oauth_providers (R2-M7: IdP group → role mapping)

Revision ID: 051
Revises: 050
Create Date: 2026-08-10

Why
---
Round-2 audit M7: `groups_claim` (migration 012) was stored but never read.
The provider may now carry a `groups_map` JSON object mapping IdP group
names to role slugs. After the OIDC callback, groups from the userinfo /
id_token claims are looked up in this map: the first mapped group wins and
becomes the provisioned (JIT) or updated role. Providers without a
groups_map keep the previous default_role behavior.

Schema
------
Adds `oauth_providers.groups_map JSONB NOT NULL DEFAULT '{}'` — a per-provider
administrator-owned mapping. Empty/absent = mapping disabled.

Rollback
--------
Drops the column; stored mappings are lost (re-enterable via the admin API).
"""

from alembic import op

revision = '051'
down_revision = '050'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE oauth_providers ADD COLUMN IF NOT EXISTS groups_map JSONB NOT NULL DEFAULT '{}'::jsonb
    """)


def downgrade():
    op.execute("ALTER TABLE oauth_providers DROP COLUMN IF EXISTS groups_map")
