"""Pre-registration stubs may be unassigned (v2.1 R2-06-06)

Revision ID: 085
Revises: 084
Create Date: 2026-08-22

ADT^Z01 stubs arrive before anyone picks a room/device. Making
resource_id nullable lets them exist as unassigned bookings; the
EXCLUDE double-book guard treats NULL resources as distinct, so
unassigned stubs never collide. Staff assign a resource at check-in.
"""

from alembic import op

revision = '085'
down_revision = '084'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE ris_appointments '
               'ALTER COLUMN resource_id DROP NOT NULL')


def downgrade():
    op.execute('DELETE FROM ris_appointments WHERE resource_id IS NULL')
    op.execute('ALTER TABLE ris_appointments '
               'ALTER COLUMN resource_id SET NOT NULL')
