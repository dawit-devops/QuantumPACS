"""RBAC: roles table, permission columns on users

Revision ID: 008
Revises: 007
Create Date: 2026-07-25

Why
---
Implements Role-Based Access Control (RBAC): creates the roles table with
JSONB permissions, adds role_id FK and oauth_sub/groups columns to users.
Seeds 7 built-in roles (super_admin, admin, technologist, radiologist,
physician, cashier, tenant_admin) with granular permission sets.

Data Migration
--------------
Seeds 7 built-in roles on CONFLICT (slug) DO NOTHING. No user data migration.

Rollback
--------
Drops columns (groups, oauth_sub, role_id) from users, drops roles table.

References
----------
- ADR-008: Role-Based Access Control design
"""

from alembic import op
from datetime import datetime, timezone

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


SEED_ROLES = [
    {
        'name': 'Super Admin',
        'slug': 'super_admin',
        'permissions': [
            'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
            'PATIENT_READ', 'PATIENT_WRITE',
            'STUDY_READ', 'STUDY_WRITE',
            'USER_READ', 'USER_WRITE', 'USER_DELETE', 'USER_ADMIN',
            'REPLICA_READ', 'REPLICA_WRITE', 'REPLICA_DELETE',
            'LOG_READ',
            'TENANT_READ', 'TENANT_WRITE', 'TENANT_ADMIN',
            'ROLE_READ', 'ROLE_WRITE', 'ROLE_DELETE',
            'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
            'WORKLIST_READ', 'WORKLIST_WRITE',
            'DICOMWEB_READ', 'DICOMWEB_WRITE',
            'ROUTING_READ', 'ROUTING_WRITE',
            'METRICS_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Administrator',
        'slug': 'admin',
        'permissions': [
            'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
            'PATIENT_READ', 'PATIENT_WRITE',
            'STUDY_READ', 'STUDY_WRITE',
            'USER_READ', 'USER_WRITE',
            'REPLICA_READ', 'REPLICA_WRITE',
            'LOG_READ',
            'ROLE_READ', 'ROLE_WRITE',
            'SERVICE_KEY_READ', 'SERVICE_KEY_WRITE', 'SERVICE_KEY_DELETE',
            'WORKLIST_READ', 'WORKLIST_WRITE',
            'DICOMWEB_READ', 'DICOMWEB_WRITE',
            'ROUTING_READ', 'ROUTING_WRITE',
            'METRICS_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Technologist',
        'slug': 'technologist',
        'permissions': [
            'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
            'PATIENT_READ', 'PATIENT_WRITE',
            'STUDY_READ', 'STUDY_WRITE',
            'WORKLIST_READ', 'WORKLIST_WRITE',
            'DICOMWEB_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Radiologist',
        'slug': 'radiologist',
        'permissions': [
            'FILE_READ',
            'PATIENT_READ',
            'STUDY_READ',
            'DICOMWEB_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Physician',
        'slug': 'physician',
        'permissions': [
            'FILE_READ',
            'PATIENT_READ',
            'STUDY_READ',
            'DICOMWEB_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Cashier',
        'slug': 'cashier',
        'permissions': [
            'PATIENT_READ',
            'PATIENT_WRITE',
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Tenant Admin',
        'slug': 'tenant_admin',
        'permissions': [
            'FILE_READ', 'FILE_WRITE', 'FILE_DELETE',
            'PATIENT_READ', 'PATIENT_WRITE',
            'STUDY_READ', 'STUDY_WRITE',
            'USER_READ', 'USER_WRITE',
            'REPLICA_READ', 'REPLICA_WRITE',
            'LOG_READ',
            'ROLE_READ', 'ROLE_WRITE',
            'WORKLIST_READ', 'WORKLIST_WRITE',
            'METRICS_READ',
        ],
        'built_in': True,
        'tenant_id': None,
    },
]


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
        built_in BOOLEAN NOT NULL DEFAULT FALSE,
        tenant_id TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS roles_slug ON roles(slug)")
    op.execute("CREATE INDEX IF NOT EXISTS roles_tenant ON roles(tenant_id)")

    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id UUID REFERENCES roles(id)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_sub TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS groups JSONB")
    op.execute("""
    COMMENT ON COLUMN users.admin IS 'DEPRECATED — use role_id for v3 permissions'
    """)

    now = datetime.now(timezone.utc).isoformat()
    for role in SEED_ROLES:
        perms_json = ', '.join(f'"{p}"' for p in role['permissions'])
        built_in_val = 'TRUE' if role['built_in'] else 'FALSE'
        tenant_val = 'NULL' if role['tenant_id'] is None else f"'{role['tenant_id']}'"
        op.execute(f"""
        INSERT INTO roles (slug, name, permissions, built_in, tenant_id, created_at, updated_at)
        VALUES (
            '{role['slug']}',
            '{role['name']}',
            '[{perms_json}]'::jsonb,
            {built_in_val},
            {tenant_val},
            '{now}'::timestamptz,
            '{now}'::timestamptz
        )
        ON CONFLICT (slug) DO NOTHING
        """)


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS groups")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oauth_sub")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role_id")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")