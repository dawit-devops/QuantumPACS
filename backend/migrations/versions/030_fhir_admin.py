"""Create fhir_config and fhir_clients tables

Revision ID: 030
Revises: 029
Create Date: 2026-07-29

Adds:
- fhir_config table for FHIR module settings (key-value)
- fhir_clients table for SMART-on-FHIR client registrations
"""

from alembic import op

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS fhir_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    INSERT INTO fhir_config (key, value) VALUES
        ('enabled', 'false'),
        ('base_url', 'http://localhost:8080/api/fhir'),
        ('publisher', 'QuantumPACS'),
        ('max_search_results', '100'),
        ('log_retention_days', '30')
    ON CONFLICT (key) DO NOTHING
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS fhir_clients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        client_id TEXT NOT NULL UNIQUE,
        client_secret TEXT NOT NULL,
        redirect_uris TEXT DEFAULT '',
        grant_type TEXT NOT NULL DEFAULT 'client_credentials',
        active BOOLEAN NOT NULL DEFAULT TRUE,
        last_used TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fhir_clients_client_id ON fhir_clients(client_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS fhir_clients CASCADE")
    op.execute("DROP TABLE IF EXISTS fhir_config CASCADE")
