"""RBAC: roles table, permission columns on users

Revision ID: 008
Revises: 007
Create Date: 2026-07-25

Adds:
- roles table with permissions JSONB
- users.role_id FK to roles
- users.oauth_sub, users.groups columns
- Seeds 5 built-in roles (admin, technologist, radiologist, physician, cashier)
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
        ],
        'built_in': True,
        'tenant_id': None,
    },
    {
        'name': 'Technologist',
        'slug': 'technologist',
        'permissions': [
            'FILE_READ', 'FILE_WRITE',
            'PATIENT_READ', 'PATIENT_WRITE',
            'STUDY_READ', 'STUDY_WRITE',
            'FILE_DELETE',
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