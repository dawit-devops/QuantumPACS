import pytest
from unittest.mock import AsyncMock, MagicMock

from services.auth.db_auth_service import DatabaseAuthService
from services.interfaces import AuthService


class FakeRecord(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class TestDatabaseAuthService:
    @pytest.fixture
    def conn(self):
        return AsyncMock()

    @pytest.fixture
    def conn_cm(self, conn):
        cm = AsyncMock()
        cm.__aenter__.return_value = conn
        return cm

    @pytest.fixture
    def svc(self, conn_cm):
        return DatabaseAuthService(conn_provider=lambda: conn_cm)

    def test_is_auth_service(self, svc):
        assert hasattr(svc, 'authenticate')
        assert hasattr(svc, 'verify_token')
        assert hasattr(svc, 'authorize')
        assert hasattr(svc, 'get_user')

    async def test_authenticate_returns_user_on_valid_login(self, svc, conn, monkeypatch):
        expected_user = FakeRecord({'id': 1, 'username': 'admin'})
        users_mock = MagicMock()
        users_mock.login = AsyncMock(return_value=expected_user)
        monkeypatch.setattr('services.auth.db_auth_service.Users', lambda c: users_mock)
        result = await svc.authenticate('admin', 'valid_password')
        assert result is not None
        assert result['username'] == 'admin'
        users_mock.login.assert_called_once_with('admin', 'valid_password')

    async def test_authenticate_returns_none_on_invalid_login(self, svc, conn, monkeypatch):
        from exceptions import ApiException
        users_mock = MagicMock()
        users_mock.login = AsyncMock(side_effect=ApiException('bad password'))
        monkeypatch.setattr('services.auth.db_auth_service.Users', lambda c: users_mock)
        result = await svc.authenticate('admin', 'wrong')
        assert result is None

    async def test_verify_token_returns_payload_on_valid_token(self, svc, monkeypatch):
        expected_payload = {'id': 1, 'admin': True}
        monkeypatch.setattr(
            'services.auth.db_auth_service.verify_token',
            lambda token: expected_payload,
        )
        result = await svc.verify_token('valid.token.here')
        assert result == expected_payload

    async def test_verify_token_returns_none_on_invalid_token(self, svc, monkeypatch):
        def raise_invalid(token):
            raise Exception('invalid token')
        monkeypatch.setattr('services.auth.db_auth_service.verify_token', raise_invalid)
        result = await svc.verify_token('invalid.token')
        assert result is None

    async def test_authorize_uses_role_slug_from_user(self, svc, monkeypatch):
        monkeypatch.setattr(
            'services.auth.db_auth_service.get_role_permissions',
            lambda role: ['read', 'write'],
        )
        result = await svc.authorize({'role': 'admin', 'id': 1}, 'write')
        assert result is True

    async def test_authorize_returns_false_when_permission_missing(self, svc, monkeypatch):
        monkeypatch.setattr(
            'services.auth.db_auth_service.get_role_permissions',
            lambda role: ['read'],
        )
        result = await svc.authorize({'role': 'cashier', 'id': 1}, 'delete')
        assert result is False

    async def test_authorize_falls_back_to_db_when_no_role_slug(self, svc, conn, monkeypatch):
        users_mock = MagicMock()
        users_mock.get_user_role = AsyncMock(return_value=('admin', ['read', 'write', 'delete']))
        monkeypatch.setattr('services.auth.db_auth_service.Users', lambda c: users_mock)
        result = await svc.authorize({'id': 1}, 'delete')
        assert result is True
        users_mock.get_user_role.assert_called_once_with(1)

    async def test_get_user_returns_user_when_found(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord({'id': 1, 'username': 'admin'})
        result = await svc.get_user(1)
        assert result is not None
        assert result['id'] == 1

    async def test_get_user_returns_none_when_not_found(self, svc, conn):
        conn.fetchrow.return_value = None
        result = await svc.get_user(999)
        assert result is None
