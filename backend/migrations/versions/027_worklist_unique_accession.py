"""Add unique index on worklist_entries.accession_number

Revision ID: 027
Revises: 026
Create Date: 2026-07-29
"""

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_worklist_accession
    ON worklist_entries(accession_number) WHERE accession_number != ''
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_worklist_accession")
