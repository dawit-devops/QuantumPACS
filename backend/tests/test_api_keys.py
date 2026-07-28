from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.api_keys import ApiKeysHandler, ApiKeyHandler
from api.auth import TokenAuth
from api.permissions import Permission


SECRET = 'test-secret-key-for-api-key-tests!!'


def _fake_auth_middleware(user):
    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Middleware(FakeAuth)


def _make_token_app():
    return Starlette(
        routes=[Route('/api/protected', endpoint=_protected)],
        middleware=[
            Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                       on_error=TokenAuth.on_auth_error),
        ],
    )


async def _protected(request):
    return JSONResponse({
        'id': request.user.id,
        'admin': request.user.admin,
        'permissions': request.user.permissions,
    })


class TestApiKeyGeneration:
    def test_generates_correct_format(self):
        result = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.generate(
            service_name='test-service'
        )
        raw_key = result['raw_key']
        assert raw_key.startswith('qpk_')
        assert len(raw_key) > 10
        prefix = result['prefix']
        assert prefix == raw_key[4:12]
        assert result['key_hash'] == __import__('hashlib').sha256(raw_key.encode()).hexdigest()

    def test_generates_unique_keys(self):
        result1 = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.generate(
            service_name='svc-a'
        )
        result2 = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.generate(
            service_name='svc-b'
        )
        assert result1['raw_key'] != result2['raw_key']
        assert result1['prefix'] != result2['prefix']

    def test_hash_is_sha256(self):
        result = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.generate(
            service_name='test'
        )
        assert len(result['key_hash']) == 64
        int(result['key_hash'], 16)

    def test_prefix_is_first_8_chars_after_qpk(self):
        result = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.generate(
            service_name='test'
        )
        raw = result['raw_key']
        assert result['prefix'] == raw[4:12]


class TestApiKeyStore:
    @pytest.mark.asyncio
    async def test_store_returns_id(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 'key-uuid-123'
        keys = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys(conn=conn)
        key_id = await keys.store(
            name='my-key', key_hash='a' * 64, prefix='abc12345',
            service_name='ingestion',
        )
        assert key_id == 'key-uuid-123'
        sql = conn.fetchval.call_args[0][0]
        assert 'INSERT INTO' in sql


class TestApiKeyToJson:
    def test_removes_key_hash(self):
        data = {
            'id': 'k1', 'name': 'test', 'key_hash': 'a' * 64,
            'prefix': 'abc12345', 'service_name': 'svc',
            'permissions': [], 'created_at': '2026-01-01',
        }
        result = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.to_json(data)
        assert 'key_hash' not in result
        assert result['service_name'] == 'svc'

    def test_strips_key_hash_from_db_row(self):
        data = {
            'id': 'k1', 'name': 'test', 'key_hash': 'a' * 64,
            'prefix': 'abc12345', 'service_name': 'svc',
            'permissions': [], 'created_at': '2026-01-01',
        }
        result = __import__('db.api_keys', fromlist=['ApiKeys']).ApiKeys.to_json(data)
        assert 'key_hash' not in result


class TestApiKeyValidation:
    @pytest.mark.asyncio
    async def test_valid_key_returns_record(self):
        from db.api_keys import ApiKeys
        conn = AsyncMock()
        raw_key = 'qpk_' + __import__('secrets').token_urlsafe(32)
        key_hash = __import__('hashlib').sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[4:12]
        conn.fetchrow.return_value = {
            'id': 'k1', 'name': 'my-key', 'key_hash': key_hash,
            'prefix': prefix, 'service_name': 'ingestion',
            'enabled': True, 'expires_at': None, 'last_used_at': None,
            'permissions': ['FILE_READ', 'FILE_WRITE'],
            'created_by': None, 'created_at': '2026-01-01',
        }
        conn.execute.return_value = None
        keys = ApiKeys(conn=conn)
        result = await keys.validate(raw_key)
        assert result is not None
        assert result['service_name'] == 'ingestion'
        assert 'key_hash' not in result
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_invalid_key_returns_none(self):
        from db.api_keys import ApiKeys
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'k1', 'name': 'my-key', 'key_hash': 'a' * 64,
            'prefix': 'abc12345', 'service_name': 'ingestion',
            'enabled': True, 'expires_at': None, 'last_used_at': None,
            'permissions': [], 'created_by': None, 'created_at': '2026-01-01',
        }
        keys = ApiKeys(conn=conn)
        result = await keys.validate('qpk_wrongkeythatdoesnotmatch')
        assert result is None

    @pytest.mark.asyncio
    async def test_revoked_key_returns_none(self):
        from db.api_keys import ApiKeys
        conn = AsyncMock()
        raw_key = 'qpk_' + __import__('secrets').token_urlsafe(32)
        key_hash = __import__('hashlib').sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[4:12]
        conn.fetchrow.return_value = {
            'id': 'k1', 'name': 'my-key', 'key_hash': key_hash,
            'prefix': prefix, 'service_name': 'ingestion',
            'enabled': False, 'expires_at': None, 'last_used_at': None,
            'permissions': [], 'created_by': None, 'created_at': '2026-01-01',
        }
        keys = ApiKeys(conn=conn)
        result = await keys.validate(raw_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_key_returns_none(self):
        from db.api_keys import ApiKeys
        conn = AsyncMock()
        from datetime import datetime, timedelta, timezone
        raw_key = 'qpk_' + __import__('secrets').token_urlsafe(32)
        key_hash = __import__('hashlib').sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[4:12]
        conn.fetchrow.return_value = {
            'id': 'k1', 'name': 'my-key', 'key_hash': key_hash,
            'prefix': prefix, 'service_name': 'ingestion',
            'enabled': True,
            'expires_at': datetime.now(timezone.utc) - timedelta(days=1),
            'last_used_at': None,
            'permissions': [], 'created_by': None, 'created_at': '2026-01-01',
        }
        keys = ApiKeys(conn=conn)
        result = await keys.validate(raw_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_prefix_returns_none(self):
        from db.api_keys import ApiKeys
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        keys = ApiKeys(conn=conn)
        result = await keys.validate('qpk_nonexistentkeyvalue')
        assert result is None


class TestApiKeyCrud:
    def _make_app(self, user):
        from api.api_keys import ApiKeysHandler, ApiKeyHandler
        return Starlette(
            routes=[
                Route('/api/api-keys', endpoint=ApiKeysHandler),
                Route('/api/api-keys/{id}', endpoint=ApiKeyHandler),
            ],
            middleware=[_fake_auth_middleware(user)],
        )

    def test_list_keys_requires_permission(self):
        user = MagicMock()
        user.is_authenticated = True
        user.permissions = []
        user.admin = False
        with patch('api.api_keys.get_conn') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_get_conn.return_value = mock_conn
            client = TestClient(self._make_app(user))
            resp = client.get('/api/api-keys')
        assert resp.status_code == 403

    def test_list_keys_with_permission(self):
        user = MagicMock()
        user.is_authenticated = True
        user.permissions = [Permission.SERVICE_KEY_READ.value]
        app = self._make_app(user)
        with patch('api.api_keys.get_conn') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_get_conn.return_value = mock_conn
            mock_keys = MagicMock()
            mock_keys.get_all = AsyncMock(return_value=[
                {'id': 'k1', 'name': 'key1', 'service_name': 'svc',
                 'prefix': 'abc12345', 'permissions': [], 'created_at': '2026-01-01'},
            ])
            with patch('api.api_keys.ApiKeys', return_value=mock_keys):
                client = TestClient(app)
                resp = client.get('/api/api-keys')
        assert resp.status_code == 200
        data = resp.json()
        assert 'data' in data
        assert len(data['data']) == 1

    def test_revoke_key_requires_permission(self):
        user = MagicMock()
        user.is_authenticated = True
        user.permissions = []
        user.admin = False
        with patch('api.api_keys.get_conn') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_get_conn.return_value = mock_conn
            client = TestClient(self._make_app(user))
            resp = client.delete('/api/api-keys/k1')
        assert resp.status_code == 403

    def test_revoke_key_with_permission(self):
        user = MagicMock()
        user.is_authenticated = True
        user.permissions = [Permission.SERVICE_KEY_DELETE.value]
        app = self._make_app(user)
        with patch('api.api_keys.get_conn') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_get_conn.return_value = mock_conn
            mock_keys = MagicMock()
            mock_keys.get = AsyncMock(return_value={
                'id': 'k1', 'name': 'key1', 'service_name': 'svc',
                'prefix': 'abc12345', 'permissions': [], 'created_at': '2026-01-01',
            })
            mock_keys.revoke = AsyncMock()
            with patch('api.api_keys.ApiKeys', return_value=mock_keys):
                client = TestClient(app)
                resp = client.delete('/api/api-keys/k1')
        assert resp.status_code == 200

    def test_revoke_missing_key_returns_404(self):
        user = MagicMock()
        user.is_authenticated = True
        user.permissions = [Permission.SERVICE_KEY_DELETE.value]
        app = self._make_app(user)
        with patch('api.api_keys.get_conn') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_get_conn.return_value = mock_conn
            mock_keys = MagicMock()
            mock_keys.get = AsyncMock(return_value=None)
            with patch('api.api_keys.ApiKeys', return_value=mock_keys):
                client = TestClient(app)
                resp = client.delete('/api/api-keys/missing')
        assert resp.status_code == 404


class TestApiKeyMiddleware:
    def test_valid_api_key_returns_200(self):
        from db.api_keys import ApiKeys
        raw_key = 'qpk_' + __import__('secrets').token_urlsafe(32)
        key_hash = __import__('hashlib').sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[4:12]

        app = _make_token_app()

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn

        async def _fake_fetchone(q):
            str_q = str(q)
            if 'prefix' in str_q:
                return {
                    'id': 'k1', 'name': 'svc-key', 'key_hash': key_hash,
                    'prefix': prefix, 'service_name': 'ingestion',
                    'enabled': True, 'expires_at': None, 'last_used_at': None,
                    'permissions': ['FILE_READ', 'FILE_WRITE'],
                    'created_by': None, 'created_at': '2026-01-01',
                }
            return None

        mock_conn.fetchrow = _fake_fetchone
        mock_conn.execute = AsyncMock()

        with (
            patch('api.auth.get_conn', return_value=mock_conn),
        ):
            client = TestClient(app)
            resp = client.get('/api/protected', headers={'X-API-Key': raw_key})

        assert resp.status_code == 200
        data = resp.json()
        assert data['id'] == 'svc_ingestion'
        assert data['admin'] is False
        assert 'FILE_READ' in data['permissions']

    def test_invalid_api_key_returns_401(self):
        app = _make_token_app()

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()

        with (
            patch('api.auth.get_conn', return_value=mock_conn),
        ):
            client = TestClient(app)
            resp = client.get('/api/protected', headers={'X-API-Key': 'qpk_invalid12345'})

        assert resp.status_code == 401

    def test_missing_api_key_falls_through_to_jwt(self):
        app = _make_token_app()

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            from api.tokens import create_token
            import jwt as _jwt
            with patch('api.auth.config', {'secret': SECRET, 'cors_origins': '*'}):
                token = create_token({'id': 1, 'admin': True}, expire={'minutes': 60})
                client = TestClient(app)
                resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})

        assert resp.status_code == 200
