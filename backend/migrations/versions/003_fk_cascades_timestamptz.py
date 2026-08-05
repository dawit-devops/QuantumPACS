"""fk cascades and timestamptz conversion

Revision ID: 003
Revises: 002
Create Date: 2026-07-23

Why
---
Converts all TIMESTAMP columns to TIMESTAMPTZ for proper timezone handling and adds
ON DELETE CASCADE on 8 foreign keys to prevent orphaned records. file_changes.by_user_id
uses ON DELETE SET NULL to preserve audit trail when a user is deleted.

Data Migration
--------------
All timestamp columns are converted IN PLACE using AT TIME ZONE 'UTC' to preserve
existing values. Default expressions are updated from `(now() at time zone 'utc')`
to plain `now()`.

Rollback
--------
Converts TIMESTAMPTZ back to TIMESTAMP, restores old default expressions, and
reverses cascading FK behavior to NO ACTION.

References
----------
- docs/DB_SCHEMA_REVIEW.md R4, R5
"""

from alembic import op


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


FK_CASCADES = [
    ('studies', 'patient_id', 'patients', 'id'),
    ('series', 'study_id', 'studies', 'id'),
    ('files', 'patient_id', 'patients', 'id'),
    ('files', 'study_id', 'studies', 'id'),
    ('files', 'series_id', 'series', 'id'),
    ('file_changes', 'file_id', 'files', 'id'),
    ('replica_files', 'replica_id', 'replicas', 'id'),
    ('replica_files', 'file_id', 'files', 'id'),
]

TSTZ_COLS = [
    ('users', 'created'),
    ('users', 'updated'),
    ('files', 'created'),
    ('files', 'updated'),
    ('file_changes', 'created'),
    ('replica_files', 'created'),
    ('replica_files', 'updated'),
    ('logs', 'created'),
    ('shared_files', 'created'),
    ('shared_files', 'expires'),
]


def _fk_name(table, column):
    return f'{table}_{column}_fkey'


def upgrade():
    # R4: TIMESTAMP → TIMESTAMPTZ
    for table, col in TSTZ_COLS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMPTZ '
            f'USING {col} AT TIME ZONE \'UTC\''
        )

    # Remove AT TIME ZONE 'utc' from defaults — now() is already UTC-aware
    op.execute(
        "ALTER TABLE users ALTER COLUMN created SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN updated SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE files ALTER COLUMN created SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE files ALTER COLUMN updated SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE file_changes ALTER COLUMN created SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE replica_files ALTER COLUMN created SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE replica_files ALTER COLUMN updated SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE logs ALTER COLUMN created SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE shared_files ALTER COLUMN created SET DEFAULT now()"
    )

    # R5: ON DELETE CASCADE on 6 FKs + ON DELETE SET NULL on file_changes.by_user_id
    for table, column, ref_table, ref_col in FK_CASCADES:
        op.execute(
            f'ALTER TABLE {table} DROP CONSTRAINT {_fk_name(table, column)}'
        )
        op.execute(
            f'ALTER TABLE {table} ADD FOREIGN KEY ({column}) '
            f'REFERENCES {ref_table}({ref_col}) ON DELETE CASCADE'
        )

    # file_changes.by_user_id → ON DELETE SET NULL (preserve audit trail)
    op.execute(
        'ALTER TABLE file_changes DROP CONSTRAINT file_changes_by_user_id_fkey'
    )
    op.execute(
        'ALTER TABLE file_changes ADD FOREIGN KEY (by_user_id) '
        'REFERENCES users(id) ON DELETE SET NULL'
    )


def downgrade():
    # Reverse: TIMESTAMPTZ → TIMESTAMP
    for table, col in TSTZ_COLS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP '
            f'USING {col} AT TIME ZONE \'UTC\''
        )

    # Restore old defaults
    for table in ('users', 'files', 'file_changes', 'replica_files'):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN created "
            f"SET DEFAULT (now() at time zone 'utc')"
        )
        if table in ('users', 'files', 'replica_files'):
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN updated "
                f"SET DEFAULT (now() at time zone 'utc')"
            )
    op.execute(
        "ALTER TABLE logs ALTER COLUMN created "
        "SET DEFAULT (now() at time zone 'utc')"
    )
    op.execute(
        "ALTER TABLE shared_files ALTER COLUMN created "
        "SET DEFAULT (now() at time zone 'utc')"
    )

    # Reverse FK changes: restore NO ACTION (default)
    for table, column, ref_table, ref_col in FK_CASCADES:
        op.execute(
            f'ALTER TABLE {table} DROP CONSTRAINT {_fk_name(table, column)}'
        )
        op.execute(
            f'ALTER TABLE {table} ADD FOREIGN KEY ({column}) '
            f'REFERENCES {ref_table}({ref_col})'
        )

    # Restore file_changes.by_user_id without SET NULL
    op.execute(
        'ALTER TABLE file_changes DROP CONSTRAINT file_changes_by_user_id_fkey'
    )
    op.execute(
        'ALTER TABLE file_changes ADD FOREIGN KEY (by_user_id) '
        'REFERENCES users(id)'
    )
