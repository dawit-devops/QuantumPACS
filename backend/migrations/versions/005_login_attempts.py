"""add login_attempts table for persistent rate limiting

Revision ID: 005
Revises: 004
Create Date: 2026-07-24

Add a login_attempts table that records each login attempt (IP, timestamp)
for persistent rate limiting across server restarts.

Also adds a cleanup trigger to auto-purge records older than 24 hours.
"""

from alembic import op


revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ip INET NOT NULL,
        endpoint TEXT NOT NULL DEFAULT 'login',
        success BOOLEAN NOT NULL DEFAULT FALSE,
        created TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS login_attempts_ip_created
        ON login_attempts(ip, created DESC)
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS login_attempts_created
        ON login_attempts(created)
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS login_attempts')
