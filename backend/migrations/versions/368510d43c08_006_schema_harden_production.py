"""production schema hardening

Revision ID: 368510d43c08
Revises: 005
Create Date: 2026-07-24 20:42:36.512155

Adds:
- Index on patients(name) for name-based lookups
- Index on logs(created) for time-range queries
- UNIQUE constraint on shared_files(hash) to prevent collisions
- Make file_changes.by_user_id nullable (ON DELETE SET NULL already set)
- Add users.needs_rehash column for legacy password upgrade path
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '368510d43c08'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_patients_name', 'patients', ['name'])
    op.create_index('idx_logs_created', 'logs', ['created'])
    op.create_unique_constraint('uq_shared_files_hash', 'shared_files', ['hash'])
    op.alter_column('file_changes', 'by_user_id', nullable=True)
    op.add_column('users', sa.Column('needs_rehash', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')))


def downgrade() -> None:
    op.drop_index('idx_patients_name', table_name='patients')
    op.drop_index('idx_logs_created', table_name='logs')
    op.drop_constraint('uq_shared_files_hash', 'shared_files', type_='unique')
    op.alter_column('file_changes', 'by_user_id', nullable=False)
    op.drop_column('users', 'needs_rehash')
