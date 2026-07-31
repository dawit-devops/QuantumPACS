import os
import tempfile

import pytest

from storage.storage import Storage


@pytest.fixture(autouse=True)
def _reset_storage_registry():
    saved = dict(Storage.storage_types)
    Storage.storages.clear()
    Storage._init_locks.clear()
    yield
    Storage.storages.clear()
    Storage._init_locks.clear()
    Storage.storage_types.update(saved)


class TestLocalStorage:
    @pytest.fixture
    def tmp_location(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def replica(self, tmp_location):
        return {'id': 1, 'type': 'local', 'location': tmp_location}

    @pytest.fixture
    def storage(self, replica):
        from storage.local_storage import LocalStorage
        return LocalStorage(replica)

    def test_name(self):
        from storage.local_storage import LocalStorage
        assert LocalStorage.name == 'local'

    def test_get_path(self, storage):
        path = storage.get_path({
            'patient_id': '100', 'study_id': '200', 'series_number': '300', 'name': 'image.dcm',
        })
        assert path == os.path.join('100', '200', '300', 'image.dcm')

    def test_get_path_empty_study(self, storage):
        path = storage.get_path({
            'patient_id': '100', 'study_id': '', 'series_number': '300', 'name': 'image.dcm',
        })
        assert path == os.path.join('100', 'empty', '300', 'image.dcm')

    def test_get_path_empty_all(self, storage):
        path = storage.get_path({
            'patient_id': '100', 'study_id': '', 'series_number': '', 'name': 'image.dcm',
        })
        assert path == os.path.join('100', 'empty', 'empty', 'image.dcm')

    def test_get_path_rejects_empty_patient_id(self, storage):
        with pytest.raises(ValueError, match='patient_id'):
            storage.get_path({
                'patient_id': '', 'study_id': '', 'series_number': '', 'name': 'test.dcm',
            })

    def test_get_path_sanitizes_special_chars(self, storage):
        path = storage.get_path({
            'patient_id': '../evil',
            'study_id': '2',
            'series_number': '3',
            'name': 'file.dcm',
        })
        assert '..' not in path
        assert path == os.path.join('evil', '2', '3', 'file.dcm')

    def test_get_path_non_ascii(self, storage):
        path = storage.get_path({
            'patient_id': 'pätiënt',
            'study_id': 'étude',
            'series_number': '3',
            'name': 'fîlé.dcm',
        })
        assert path == os.path.join('ptint', 'tude', '3', 'fl.dcm')

    def test_get_path_empty_name_becomes_dot(self, storage):
        path = storage.get_path({
            'patient_id': '1',
            'study_id': '2',
            'series_number': '',
            'name': '',
        })
        assert path == os.path.join('1', '2', 'empty', '.')

    async def test_init_creates_directory(self, tmp_location, storage):
        subdir = os.path.join(tmp_location, 'nonexistent_sub')
        storage.location = subdir
        assert not os.path.exists(subdir)
        await storage.init()
        assert os.path.exists(subdir)

    async def test_copy_creates_dirs_and_copies_file(self, tmp_location, storage):
        src = os.path.join(tmp_location, 'src.dcm')
        with open(src, 'w') as f:
            f.write('dicom data')

        result = await storage.copy(src, {
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'test.dcm',
        })

        dst = os.path.join(tmp_location, '1', '2', '3', 'test.dcm')
        assert os.path.exists(dst)
        assert result['location'] == dst
        with open(dst) as f:
            assert f.read() == 'dicom data'

    async def test_copy_from_fileobj(self, tmp_location, storage):
        from io import BytesIO
        buf = BytesIO(b'fileobj content')

        await storage.copy(buf, {
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'from-obj.dcm',
        })

        dst = os.path.join(tmp_location, '1', '2', '3', 'from-obj.dcm')
        assert os.path.exists(dst)
        with open(dst) as f:
            assert f.read() == 'fileobj content'

    async def test_fetch_returns_path(self, storage, tmp_location):
        file_path = os.path.join(tmp_location, 'exists.dcm')
        with open(file_path, 'w') as f:
            f.write('data')

        result = await storage.fetch({'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'exists.dcm'})

        assert result == os.path.join(tmp_location, '1', '2', '3', 'exists.dcm')

    async def test_serve_returns_fileresponse(self, storage, tmp_location):
        file_dir = os.path.join(tmp_location, '1', '2', '3')
        os.makedirs(file_dir)
        file_path = os.path.join(file_dir, 'serve.dcm')
        with open(file_path, 'w') as f:
            f.write('data')

        result = await storage.serve({'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'serve.dcm'})

        assert result.status_code == 200
        assert hasattr(result, 'path')

    async def test_delete_removes_file(self, storage, tmp_location):
        file_dir = os.path.join(tmp_location, '1', '2', '3')
        os.makedirs(file_dir)
        file_path = os.path.join(file_dir, 'delete.dcm')
        with open(file_path, 'w') as f:
            f.write('data')
        assert os.path.exists(file_path)

        await storage.delete({'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'delete.dcm'})

        assert not os.path.exists(file_path)

    async def test_delete_ignores_missing_file(self, storage):
        await storage.delete({'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'missing.dcm'})

    def test_default_config(self):
        from storage.local_storage import LocalStorage
        cfg = LocalStorage.default_config()
        assert 'location' in cfg
        assert os.path.isabs(cfg['location'])

    def test_index_yields_entries(self, storage, tmp_location):
        file_dir = os.path.join(tmp_location, '1', '2', '3')
        os.makedirs(file_dir)
        file_path = os.path.join(file_dir, 'test.dcm')
        with open(file_path, 'w') as f:
            f.write('data')

        import asyncio
        async def _collect():
            results = []
            async for entry in storage.index():
                results.append(entry)
            return results

        results = asyncio.run(_collect())
        assert len(results) >= 1
        matching = [r for r in results if r['name'] == 'test.dcm']
        assert len(matching) == 1
        assert matching[0]['patient_id'] == '1'

    async def test_copy_permission_error_retries(self, storage, tmp_location):
        src = os.path.join(tmp_location, 'src.dcm')
        with open(src, 'w') as f:
            f.write('data')

        original_copy = storage._copy
        call_count = [0]

        def _failing_copy(src_path, dst_path):
            call_count[0] += 1
            if call_count[0] == 1:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(dst_path, 'w') as f:
                    f.write('partial')
                raise PermissionError
            original_copy(src_path, dst_path)

        storage._copy = _failing_copy

        await storage.copy(src, {
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'retry.dcm',
        })

        dst = os.path.join(tmp_location, '1', '2', '3', 'retry.dcm')
        assert os.path.exists(dst)
        assert call_count[0] == 2
