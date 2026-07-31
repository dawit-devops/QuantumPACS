"""Create notifications table

Revision ID: 029
Revises: 028
Create Date: 2026-07-29

Adds notification infrastructure for in-app alerts.
"""

from alembic import op

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        link TEXT,
        read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications(user_id) WHERE NOT read")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_created ON notifications(created_at DESC)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
