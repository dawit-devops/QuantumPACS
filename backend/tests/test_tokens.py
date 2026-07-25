from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest

from api.tokens import create_token, verify_token


class TestTokens:
    SECRET = 'test-secret-key-32-bytes-long!!!'

    @pytest.fixture
    def user(self):
        return {'id': 42, 'admin': True}

    def test_create_token_returns_string(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_returns_payload(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            payload = verify_token(token)
        assert payload['id'] == 42
        assert payload['admin'] is True

    def test_token_has_exp_claim(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            payload = verify_token(token)
        assert 'exp' in payload
        assert isinstance(payload['exp'], int)

    def test_token_expires_after_14_days(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            payload = verify_token(token)
        exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert timedelta(days=13) < (exp - now) < timedelta(days=15)

    def test_token_with_custom_expiry(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user, expire={'hours': 1})
            payload = verify_token(token)
        exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert timedelta(minutes=59) < (exp - now) < timedelta(hours=2)

    def test_expired_token_raises(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user, expire={'days': -1})
            with pytest.raises(jwt.InvalidTokenError):
                verify_token(token)

    def test_invalid_signature_raises(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
        with patch('api.tokens.config', {'secret': 'different-secret-key-32-bytes!!!'}):
            with pytest.raises(jwt.InvalidSignatureError):
                verify_token(token)

    def test_tampered_token_raises(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            parts = token.split('.')
            tampered = parts[0] + '.' + parts[1] + '.invalidsig'
            with pytest.raises(jwt.InvalidTokenError):
                verify_token(tampered)

    def test_admin_false_token(self):
        user = {'id': 1, 'admin': False}
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            payload = verify_token(token)
        assert payload['admin'] is False

    def test_create_token_admin_flag_preserved(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
        decoded = jwt.decode(token, self.SECRET, algorithms=['HS256'])
        assert decoded['admin'] is True
        assert decoded['id'] == 42

    def test_create_token_with_role(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user, role='admin', permissions=['files:read', 'files:write'])
            payload = verify_token(token)
        assert payload['role'] == 'admin'
        assert 'files:read' in payload['permissions']

    def test_create_token_without_role_no_claims(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user)
            payload = verify_token(token)
        assert 'role' not in payload

    def test_create_token_empty_permissions(self, user):
        with patch('api.tokens.config', {'secret': self.SECRET}):
            token = create_token(user, role='viewer', permissions=[])
            payload = verify_token(token)
        assert payload['role'] == 'viewer'
        assert payload['permissions'] == []
