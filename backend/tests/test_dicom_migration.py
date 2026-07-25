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


@pytest.fixture(scope="module")
def migration_018():
    mod = importlib.import_module("migrations.versions.018_worklist")
    return mod


class TestMigration018Structure:
    def test_revision_number(self, migration_018):
        assert migration_018.revision == "018"

    def test_down_revision(self, migration_018):
        assert migration_018.down_revision == "017"

    def test_upgrade_is_callable(self, migration_018):
        assert callable(migration_018.upgrade)

    def test_downgrade_is_callable(self, migration_018):
        assert callable(migration_018.downgrade)

    def test_upgrade_creates_worklist_entries(self, migration_018):
        source = inspect.getsource(migration_018.upgrade)
        assert "CREATE TABLE" in source
        assert "worklist_entries" in source

    def test_upgrade_has_required_columns(self, migration_018):
        source = inspect.getsource(migration_018.upgrade)
        required = ["patient_id", "patient_name", "accession_number",
                     "modality", "status", "scheduled_date"]
        for col in required:
            assert col in source, f"Missing column: {col}"
