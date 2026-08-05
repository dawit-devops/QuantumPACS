"""serial to bigint identity

Revision ID: 004
Revises: 003
Create Date: 2026-07-23

Why
---
Converts all 10 SERIAL primary keys to BIGINT GENERATED ALWAYS AS IDENTITY.
SERIAL (INTEGER + sequence) caps at ~2B rows; BIGINT removes this limit.
IDENTITY is SQL-standard and prevents manual PK override.

Tables: users, patients, studies, series, files, file_changes,
        replicas, replica_files, logs, shared_files

Data Migration
--------------
Drops existing sequences, changes column type to BIGINT, attaches IDENTITY.
Existing ID values are preserved as-is.

Rollback
--------
Drops IDENTITY, recreates sequences, changes back to INTEGER.

References
----------
- docs/DB_SCHEMA_REVIEW.md R6/R7
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
