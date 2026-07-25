"""add notify trigger on files table for event bridge

Revision ID: 007
Revises: 368510d43c08
Create Date: 2026-07-25

Adds a trigger on the files table using the existing notify_event() function
so that file INSERT/UPDATE/DELETE events can be bridged to Redis Streams.
"""

from alembic import op


revision = '007'
down_revision = '368510d43c08'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TRIGGER IF EXISTS notify_file_event ON files")
    op.execute("""
    CREATE TRIGGER notify_file_event
    AFTER INSERT OR UPDATE OR DELETE ON files
      FOR EACH ROW EXECUTE PROCEDURE notify_event()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS notify_file_event ON files")