"""add report_images table for representative key images

Revision ID: 113
Revises: 112
Create Date: 2026-08-28

Why
---
The reading console needs a space for the radiologist to capture 2-3
representative key images from the live viewer and attach them to the report.
These images are rendered in the final report document alongside the
findings/impression. This migration creates the storage table.

Rollback
--------
DROP TABLE report_images. Safe: additive, feature just shipped.
"""

import sqlalchemy as sa
from alembic import op

revision = '113'
down_revision = '112'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'report_images',
        sa.Column('id', sa.BigInteger(), primary_key=True,
                  autoincrement=True),
        sa.Column('report_id', sa.Uuid(), nullable=False),
        sa.Column('image_data', sa.Text(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=False, server_default=''),
        sa.Column('position', sa.SmallInteger(), nullable=False,
                  server_default='0'),
        sa.Column('created_by', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index('ix_report_images_report', 'report_images',
                    ['report_id'])
    op.create_foreign_key(
        'fk_report_images_report',
        'report_images', 'reports',
        ['report_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade():
    op.drop_constraint('fk_report_images_report', 'report_images',
                       type_='foreignkey')
    op.drop_index('ix_report_images_report', 'report_images')
    op.drop_table('report_images')