"""Create fhir_audit table

Revision ID: 022
Revises: 021
Create Date: 2026-07-26

Why
---
Creates the fhir_audit table for FHIR API request audit trail, capturing
HTTP method, path, query params, resource type/ID, status code, duration,
and client IP for compliance and debugging.

Data Migration
--------------
None — new table only.

Rollback
--------
Drops the fhir_audit table.

References
----------
- ADR-022: FHIR audit logging design
"""

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS fhir_audit (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id INTEGER DEFAULT 0,
        method TEXT NOT NULL DEFAULT '',
        path TEXT NOT NULL DEFAULT '',
        query_params TEXT DEFAULT '',
        resource_type TEXT DEFAULT '',
        resource_id TEXT DEFAULT '',
        status_code INTEGER DEFAULT 0,
        duration_ms INTEGER DEFAULT 0,
        ip_address TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fhir_audit_created ON fhir_audit(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fhir_audit_user ON fhir_audit(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fhir_audit_resource ON fhir_audit(resource_type, resource_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS fhir_audit CASCADE")
