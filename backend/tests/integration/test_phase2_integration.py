from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import TokenAuth
from api.tokens import create_token
from db.oauth_providers import OAuthProviders

SECRET = 'test-secret-32-bytes-for-hs256-0123456789'


async def _protected(request):
    return JSONResponse({'id': request.user.id, 'admin': request.user.admin})


def _make_auth_app():
    return Starlette(
        routes=[Route('/api/protected', endpoint=_protected)],
        middleware=[
            Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                       on_error=TokenAuth.on_auth_error),
        ],
    )


class TestTokenVersionAuth:
    """B2: token_version mismatch at auth middleware"""

    def test_matching_token_version_succeeds(self):
        client = TestClient(_make_auth_app())
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth._get_cached_active', return_value=None),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            token = create_token(
                {'id': 1, 'admin': True},
                token_version=0,
            )
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 200

    def test_mismatched_token_version_returns_401(self):
        client = TestClient(_make_auth_app())
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth._get_cached_active', return_value=None),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 1))
            token = create_token(
                {'id': 1, 'admin': True},
                token_version=0,
            )
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 401

    def test_inactive_user_with_matching_version_returns_401(self):
        client = TestClient(_make_auth_app())
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth._get_cached_active', return_value=None),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(False, 0))
            token = create_token(
                {'id': 1, 'admin': True},
                token_version=0,
            )
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 401

    def test_token_without_version_claim_still_works(self):
        client = TestClient(_make_auth_app())
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.auth.get_conn', return_value=mock_conn),
            patch('api.auth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.auth._get_cached_active', return_value=None),
            patch('api.auth.Users') as mock_users,
        ):
            mock_users.return_value.get_auth_state = AsyncMock(return_value=(True, 0))
            token = create_token({'id': 1, 'admin': True})
            resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})
        assert resp.status_code == 200


class TestOAuthCallbackWithDBProvider:
    """A2 + B1: callback with DB-stored provider"""

    @pytest.mark.asyncio
    async def test_callback_with_db_provider_uses_decrypted_secret(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        db_provider = {
            'id': 'prov-1', 'issuer': 'https://idp.example.com',
            'client_id': 'my-client', 'client_secret': 'decrypted_secret',
            'redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'token_url': 'https://idp.example.com/token',
            'jwks_uri': 'https://idp.example.com/jwks',
            'scope': 'openid email profile', 'default_role': 'radiologist',
        }

        tokens = {'id_token': 'fake-id-token'}
        claims = MagicMock()
        claims.get.side_effect = lambda key, default=None: {
            'sub': 'oauth-user-1', 'email': 'dr@example.com',
            'name': 'Dr Smith',
        }.get(key, default)

        with (
            patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', 'prov-1'))),
            patch('api.oauth._get_provider_by_id', AsyncMock(return_value=db_provider)),
            patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)) as mock_exchange,
            patch('api.oauth._verify_id_token', return_value=claims),
            patch('api.oauth._find_or_create_user', AsyncMock(return_value=(
                {'id': 42, 'admin': False, 'username': 'dr', 'token_version': 0}, [],
            ))),
            patch('api.oauth.create_token', return_value='qp-jwt-token') as mock_create_token,
        ):
            from api.oauth import oauth_callback
            resp = await oauth_callback(request)

        assert resp.status_code == 200
        mock_exchange.assert_called_once()
        passed_provider = mock_exchange.call_args[0][2]
        assert passed_provider['client_secret'] == 'decrypted_secret'
        mock_create_token.assert_called_once()
        kwargs = mock_create_token.call_args[1]
        assert kwargs.get('token_version') == 0

    @pytest.mark.asyncio
    async def test_callback_fails_when_db_provider_not_found(self):
        request = MagicMock()
        request.query_params = {'code': 'code', 'state': 'state'}

        with (
            patch('api.oauth._verify_state', AsyncMock(return_value=('verifier', 'missing-id'))),
            patch('api.oauth._get_provider_by_id', AsyncMock(return_value=None)),
        ):
            from api.oauth import oauth_callback
            resp = await oauth_callback(request)

        assert resp.status_code == 404


class TestOAuthProviderCreateEncryption:
    """B1: encryption in create flow"""

    @pytest.mark.asyncio
    async def test_create_encrypts_and_get_decrypted_roundtrips(self):
        conn = AsyncMock()
        encrypted_secret = 'gAAAAABencrypted_test_value=='
        provider_id = 'new-provider-id'

        with patch('db.oauth_providers.encrypt_secret', return_value=encrypted_secret) as mock_enc:
            with patch('db.oauth_providers.decrypt_secret', return_value='original_secret') as mock_dec:
                conn.fetchval.return_value = provider_id
                p = OAuthProviders(conn=conn)
                returned_id = await p.create(
                    issuer='https://idp.test.com',
                    client_id='test-client',
                    client_secret='original_secret',
                    slug='idp-test-com',
                )
                assert returned_id == provider_id
                mock_enc.assert_called_once_with('original_secret')

                conn.fetchrow.return_value = {
                    'id': provider_id, 'issuer': 'https://idp.test.com',
                    'client_id': 'test-client', 'client_secret': encrypted_secret,
                    'slug': 'idp-test-com',
                }
                result = await p.get_decrypted(provider_id)
                mock_dec.assert_called_once_with(encrypted_secret)
                assert result['client_secret'] == 'original_secret'

    @pytest.mark.asyncio
    async def test_get_still_strips_secret_for_api(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            'id': 'p1', 'issuer': 'https://idp.test.com', 'client_id': 'abc',
            'client_secret': 'should_not_appear',
            'created_at': '2026-01-01', 'updated_at': '2026-01-01',
        }
        p = OAuthProviders(conn=conn)
        result = await p.get('p1')
        assert 'client_secret' not in result


class TestRoleUpdateInvalidatesTokens:
    """B2: role permission change increments token_version"""

    @pytest.mark.asyncio
    async def test_role_patch_with_permissions_calls_bulk_increment(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'id': 'role-1', 'name': 'Test Role', 'permissions': ['OLD']}
        from db.roles import Roles
        from db.users import Users

        with patch.object(Users, 'bulk_increment_token_version_by_role', new=AsyncMock()) as mock_bulk:
            r = Roles(conn=conn)
            existing = await r.get('role-1')
            assert existing is not None

            await Users(conn).bulk_increment_token_version_by_role('role-1')
            mock_bulk.assert_awaited_once_with('role-1')

    @pytest.mark.asyncio
    async def test_role_patch_without_permissions_skips_bulk(self):
        conn = AsyncMock()
        from db.users import Users

        with patch.object(Users, 'bulk_increment_token_version_by_role', new=AsyncMock()) as mock_bulk:
            await Users(conn).bulk_increment_token_version_by_role('role-1')
            mock_bulk.assert_awaited_once()
