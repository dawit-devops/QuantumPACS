from pathlib import Path

import pytest


class TestNotifyEventMigration:
    def test_migration_025_exists(self):
        migrations_dir = Path(__file__).parents[1] / 'migrations' / 'versions'
        migration_025 = migrations_dir / '025_fix_notify_event.py'
        assert migration_025.exists(), "Migration 025 must exist"

    def test_migration_025_uses_coalesce_for_old(self):
        migrations_dir = Path(__file__).parents[1] / 'migrations' / 'versions'
        migration_025 = migrations_dir / '025_fix_notify_event.py'
        content = migration_025.read_text()
        assert "COALESCE(row_to_json(OLD), '{}'::json)" in content

    def test_migration_025_uses_coalesce_for_new(self):
        migrations_dir = Path(__file__).parents[1] / 'migrations' / 'versions'
        migration_025 = migrations_dir / '025_fix_notify_event.py'
        content = migration_025.read_text()
        assert "COALESCE(row_to_json(NEW), '{}'::json)" in content

    def test_migration_025_downgrade_restores_original(self):
        migrations_dir = Path(__file__).parents[1] / 'migrations' / 'versions'
        migration_025 = migrations_dir / '025_fix_notify_event.py'
        content = migration_025.read_text()
        assert "def downgrade()" in content
        assert "row_to_json(OLD)" in content
        assert "row_to_json(NEW)" in content
