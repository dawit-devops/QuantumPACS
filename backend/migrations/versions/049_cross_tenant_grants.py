"""Cross-tenant clinical read grants (teleradiology / telemedicine)

Revision ID: 049
Revises: 048
Create Date: 2026-08-09

Why
---
R2-03 (PACS audit 2026-08-06): a user could only access their JWT claim
tenant or admin. Telemedicine and teleradiology users must be able to read
workload from other tenants they are explicitly granted to, with every
cross-tenant access audit-logged.

This migration adds:
1. user_tenant_grants — the grant table (main DB): (user_id, tenant_slug)
   rows are the opt-in cross-tenant rights for clinical roles. Grants are
   gated by the CROSS_TENANT_READ permission: without it, a grant row is
   inert (defense in depth — permission and grant must both be present).
2. CROSS_TENANT_READ is added to the radiologist and teleradiologist
   built-in roles. The two roles must keep identical grants (RBAC spec §5
   RAD == TEL), so both are updated by the same statement.

Schema
------
New table user_tenant_grants (main DB only — grants are global, not
per-tenant); roles.permissions (jsonb) gains CROSS_TENANT_READ on the two
clinical roles.

Rollback
--------
Drops the table and removes the code from those two roles.
"""

from alembic import op

revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None

# The permission every grant-bearing user must also hold (gates the grant).
CROSS_TENANT_READ = 'CROSS_TENANT_READ'

# Clinical roles allowed to hold cross-tenant grants — RAD == TEL (§5).
AFFECTED_ROLES = ('radiologist', 'teleradiologist')


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS user_tenant_grants (
        id BIGSERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        tenant_slug TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT 'read',
        created_by TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (user_id, tenant_slug)
    );
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS uxg_tenant_slug ON user_tenant_grants(tenant_slug)
    """)
    # Idempotent: only ever adds the code, never rewrites other grants.
    for slug in AFFECTED_ROLES:
        op.execute(
            f"""
            UPDATE roles SET
                permissions = permissions || '["{CROSS_TENANT_READ}"]'::jsonb,
                updated_at = now()
            WHERE slug = '{slug}' AND built_in = TRUE
              AND NOT (permissions ? '{CROSS_TENANT_READ}')
            """
        )


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_tenant_grants")
    for slug in AFFECTED_ROLES:
        op.execute(
            f"""
            UPDATE roles SET
                permissions = permissions - '{CROSS_TENANT_READ}',
                updated_at = now()
            WHERE slug = '{slug}' AND built_in = TRUE
            """
        )