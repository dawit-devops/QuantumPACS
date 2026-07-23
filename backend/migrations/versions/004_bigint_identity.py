"""serial to bigint identity

Revision ID: 004
Revises: 003
Create Date: 2026-07-23

See docs/DB_SCHEMA_REVIEW.md R6/R7.

Convert all 10 SERIAL PKs to BIGINT GENERATED ALWAYS AS IDENTITY.
- SERIAL is legacy (INTEGER + sequence) — max ~2B rows
- BIGINT IDENTITY is SQL standard, prevents manual override

Tables: users, patients, studies, series, files, file_changes,
        replicas, replica_files, logs, shared_files
"""

from alembic import op


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

TABLES = [
    'users', 'patients', 'studies', 'series', 'files',
    'file_changes', 'replicas', 'replica_files', 'logs', 'shared_files',
]


def upgrade():
    for table in TABLES:
        seq = f'{table}_id_seq'
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id TYPE BIGINT')
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT')
        op.execute(f'DROP SEQUENCE IF EXISTS {seq} CASCADE')
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY')


def downgrade():
    # Reverse: BIGINT → INTEGER, IDENTITY → SERIAL
    for table in reversed(TABLES):
        seq = f'{table}_id_seq'
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id DROP IDENTITY IF EXISTS')
        op.execute(f'CREATE SEQUENCE IF NOT EXISTS {seq} AS INTEGER OWNED BY {table}.id')
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{seq}')")
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id TYPE INTEGER')
