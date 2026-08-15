"""Platform-admin ops: notification prefs, maintenance state, settings, backups

Revision ID: 060
Revises: 059
Create Date: 2026-08-14

Why
---
The super_admin user-feature review (docs/user-feature-review/super-admin/)
found platform-ops gaps that the audit trail already knows about but the
product has no state or control for:

- notification_prefs: per-user event-type subscriptions so the platform
  admin can mute clinical noise (study.arrived) while keeping operational
  alerts (storage.quota_breach). Absent rows resolve to role defaults.
- platform_state: durable key/value for the maintenance-mode flag (+
  reason/since), read by the write-gate middleware and the public status
  endpoint. Survives restarts, unlike a process-local flag.
- system_settings: whitelisted config overrides edited from the Settings
  page; merged over config.py defaults/env at startup so the platform
  admin can tune runtime-safe keys without SSH.
- backups: registry of on-demand metadata-manifest backups (status, artifact
  key on the master replica storage, file/byte counts, creator) so the
  Backups page and the audit events system.backup_completed/failed have a
  backing table.

All four tables are additive; nothing existing is altered.

Rollback
--------
Drops the four tables. Safe: no pre-existing data lives in them.
"""

import sqlalchemy as sa
from alembic import op

revision = '060'
down_revision = '059'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notification_prefs',
        sa.Column('user_id', sa.BigInteger(), primary_key=True),
        sa.Column('event_type', sa.Text(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
    )
    op.create_index(
        'ix_notification_prefs_user', 'notification_prefs', ['user_id'],
    )

    op.create_table(
        'platform_state',
        sa.Column('key', sa.Text(), primary_key=True),
        sa.Column('value', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    op.create_table(
        'system_settings',
        sa.Column('key', sa.Text(), primary_key=True),
        sa.Column('value', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    op.create_table(
        'backups',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True),
                  primary_key=True),
        sa.Column('status', sa.Text(), nullable=False,
                  server_default='running'),
        sa.Column('kind', sa.Text(), nullable=False, server_default='metadata'),
        sa.Column('artifact_key', sa.Text(), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False,
                  server_default='0'),
        sa.Column('files_count', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('bytes_count', sa.BigInteger(), nullable=False,
                  server_default='0'),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_backups_created_at', 'backups', ['created_at'])


def downgrade():
    op.drop_table('backups')
    op.drop_table('system_settings')
    op.drop_table('platform_state')
    op.drop_index('ix_notification_prefs_user', table_name='notification_prefs')
    op.drop_table('notification_prefs')
