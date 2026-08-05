"""Add oauth_providers table for multi-provider OAuth support

Revision ID: 012
Revises: 011
Create Date: 2026-07-25

Why
---
Creates the oauth_providers table for multi-provider OAuth/OpenID Connect support,
storing per-provider configuration (issuer, client credentials, JWKS URI, scopes)
with optional tenant scoping.

Data Migration
--------------
None — new table only.

Rollback
--------
Drops the oauth_providers table.

References
----------
- ADR-009: OAuth integration design
"""

from alembic import op

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS oauth_providers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT,
        issuer TEXT NOT NULL,
        client_id TEXT NOT NULL,
        client_secret TEXT NOT NULL DEFAULT '',
        jwks_uri TEXT,
        token_url TEXT,
        redirect_uri TEXT,
        scope TEXT DEFAULT 'openid email profile',
        groups_claim TEXT DEFAULT 'groups',
        auto_provision BOOLEAN DEFAULT TRUE,
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now()
    )
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS oauth_providers")
