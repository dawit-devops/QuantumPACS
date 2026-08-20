"""Create ris_results_distribution (CR-8)

Revision ID: 074
Revises: 073
Create Date: 2026-08-20

The ResultsDistributionEngine previously created this table lazily at runtime
(`CREATE TABLE IF NOT EXISTS`), so the DeliveryStatusHandler 500'd until the
engine happened to run. The table is now schema-managed by Alembic and includes
tenant_id for RLS parity with ris_critical_results.
"""
from alembic import op

revision = '074'
down_revision = '073'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS ris_results_distribution (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id UUID NOT NULL,
            accession_number TEXT,
            status TEXT NOT NULL DEFAULT 'SENT',
            attempts INT DEFAULT 1,
            payload TEXT,
            delivered_at TIMESTAMPTZ,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ris_distribution_report
        ON ris_results_distribution (report_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ris_distribution_status
        ON ris_results_distribution (status)
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS ris_results_distribution')