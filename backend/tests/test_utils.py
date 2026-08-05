import hashlib
from io import BytesIO

from utils import hash_file, rand_str


class TestHashFile:
    def test_hash_string_path(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        h = hash_file(str(f))
        assert h == hashlib.sha256(b"hello world").hexdigest()
        assert len(h) == 64

    def test_hash_bytesio(self):
        buf = BytesIO(b"hello world")
        h = hash_file(buf)
        assert h == hashlib.sha256(b"hello world").hexdigest()

    def test_hash_empty(self):
        buf = BytesIO(b"")
        h = hash_file(buf)
        assert h == hashlib.sha256(b"").hexdigest()

    def test_hash_large_file(self, tmp_path):
        f = tmp_path / "large.bin"
        data = b"a" * 100000
        f.write_bytes(data)
        h = hash_file(str(f))
        assert h == hashlib.sha256(data).hexdigest()

    def test_rand_str_length(self):
        s = rand_str(32)
        assert len(s) == 64
        s = rand_str(16)
        assert len(s) == 32
        s = rand_str()
        assert len(s) == 128
