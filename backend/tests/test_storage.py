import os
import pytest

from storage.storage import Storage


class TestStorageBase:
    def test_register_and_get_class(self):
        assert Storage.get_class('local') is not None
        assert Storage.get_class('s3') is not None
        assert Storage.get_class('b2') is not None

    def test_default_config_by_type(self):
        cfg = Storage.default_config_by_type('local')
        assert 'location' in cfg
        cfg = Storage.default_config_by_type('s3')
        assert 'location' in cfg
        cfg = Storage.default_config_by_type('b2')
        assert 'location' in cfg

    def test_get_class_invalid(self):
        with pytest.raises(KeyError):
            Storage.get_class('invalid')


class TestLocalStorage:
    def test_get_path_normalizes_traversal(self):
        from storage.local_storage import LocalStorage
        s = LocalStorage({'id': 1, 'location': '/tmp/storage', 'type': 'local'})
        path = s.get_path({
            'patient_id': '1',
            'study_id': '2',
            'series_number': '3',
            'name': 'file.dcm',
        })
        assert '..' not in path
        assert path == os.path.join('1', '2', '3', 'file.dcm')

    def test_get_path_rejects_traversal(self):
        from storage.local_storage import LocalStorage
        s = LocalStorage({'id': 1, 'location': '/tmp/storage', 'type': 'local'})
        path = s.get_path({
            'patient_id': '../../etc',
            'study_id': '2',
            'series_number': '3',
            'name': 'passwd',
        })
        assert '..' not in path
        assert '/etc' not in path
        assert path == os.path.join('etc', '2', '3', 'passwd')
