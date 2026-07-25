import importlib
import inspect

import pytest


@pytest.fixture(scope="module")
def migration_017():
    mod = importlib.import_module("migrations.versions.017_uids")
    return mod


class TestMigration017Structure:
    def test_revision_number(self, migration_017):
        assert migration_017.revision == "017"

    def test_down_revision(self, migration_017):
        assert migration_017.down_revision == "016"

    def test_upgrade_is_callable(self, migration_017):
        assert callable(migration_017.upgrade)

    def test_downgrade_is_callable(self, migration_017):
        assert callable(migration_017.downgrade)

    def test_upgrade_alters_studies(self, migration_017):
        source = inspect.getsource(migration_017.upgrade)
        assert "ALTER TABLE studies" in source
        assert "study_instance_uid" in source
        assert "accession_number" in source

    def test_upgrade_alters_series(self, migration_017):
        source = inspect.getsource(migration_017.upgrade)
        assert "ALTER TABLE series" in source
        assert "series_instance_uid" in source

    def test_upgrade_alters_files(self, migration_017):
        source = inspect.getsource(migration_017.upgrade)
        assert "ALTER TABLE files" in source
        assert "sop_instance_uid" in source
