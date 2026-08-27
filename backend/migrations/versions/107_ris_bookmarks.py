"""Study bookmarks and collections tables — R-08.

Revision ID: 107
Revises: 106
Create Date: 2026-08-27

Why
---
The RIS program (docs/ui-ux-redesign-spec.md R-08) needs study bookmarks
and collections for teaching, research, and follow-up. Two tables:
bookmark_collections (per-user named collections) and study_bookmarks
(study references bound to a user + optional collection).

Rollback
--------
DROP TABLE study_bookmarks, bookmark_collections. Safe: no production
data (feature not shipped).
"""

import sqlalchemy as sa
from alembic import op

revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bookmark_collections',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False,
                  server_default='default'),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('is_shared', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_bookmark_collections_user',
                    'bookmark_collections', ['tenant_id', 'user_id'])

    op.create_table(
        'study_bookmarks',
        sa.Column('id', sa.Uuid(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.Text(), nullable=False,
                  server_default='default'),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('study_uid', sa.Text(), nullable=False),
        sa.Column('study_desc', sa.Text(), server_default=''),
        sa.Column('collection_id', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_study_bookmarks_user',
                    'study_bookmarks', ['tenant_id', 'user_id'])
    op.create_index('ix_study_bookmarks_study',
                    'study_bookmarks', ['study_uid'])


def downgrade():
    op.drop_table('study_bookmarks')
    op.drop_table('bookmark_collections')