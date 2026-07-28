from unittest.mock import patch

import pytest

from api.encryption import encrypt_secret, decrypt_secret


class TestEncryption:
    def test_roundtrip_encrypt_decrypt(self):
        plain = 'my-super-secret-client-secret-12345'
        encrypted = encrypt_secret(plain)
        assert encrypted != plain
        decrypted = decrypt_secret(encrypted)
        assert decrypted == plain

    def test_encrypted_output_differs_each_call(self):
        plain = 'same-secret'
        e1 = encrypt_secret(plain)
        e2 = encrypt_secret(plain)
        assert e1 != e2

    def test_empty_string_returns_empty(self):
        assert encrypt_secret('') == ''
        assert decrypt_secret('') == ''

    def test_decrypt_legacy_plaintext_fallback(self):
        legacy = 'legacy-plaintext-secret'
        decrypted = decrypt_secret(legacy)
        assert decrypted == legacy

    def test_decrypt_invalid_ciphertext_fallback(self):
        decrypted = decrypt_secret('not-a-valid-fernect-token!!')
        assert decrypted == 'not-a-valid-fernect-token!!'

    def test_long_secret_roundtrip(self):
        long_secret = 'x' * 1000
        encrypted = encrypt_secret(long_secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == long_secret

    def test_special_characters_roundtrip(self):
        special = 'client_secret!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
        encrypted = encrypt_secret(special)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == special

    def test_unicode_roundtrip(self):
        unicode_val = 'café_ñuño_日本語_Кириллица'
        encrypted = encrypt_secret(unicode_val)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == unicode_val

    def test_decrypt_secret_with_none_config_key(self):
        with patch('api.encryption.config', {'secret': 'fallback-secret', 'oauth_secret_encryption_key': ''}):
            encrypted = encrypt_secret('test-value')
            decrypted = decrypt_secret(encrypted)
            assert decrypted == 'test-value'
