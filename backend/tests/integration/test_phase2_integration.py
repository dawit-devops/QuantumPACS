from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import TokenAuth, User
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
            'enabled': True,
        }

        tokens = {'id_token': 'fake-id-token'}
        claims = MagicMock()
        claims.get.side_effect = lambda key, default=None: {
            'sub': 'oauth-user-1', 'email': 'dr@example.com',
            'name': 'Dr Smith',
        }.get(key, default)

        with (
            patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', 'prov-1', None))),
            patch('api.oauth._get_provider_by_id', AsyncMock(return_value=db_provider)),
            patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)) as mock_exchange,
            patch('api.oauth._verify_id_token', return_value=claims),
            patch('api.oauth._find_or_create_user', AsyncMock(return_value={
                'id': 42, 'admin': False, 'username': 'dr', 'token_version': 0,
            })),
            patch('api.oauth.create_token_pair', return_value=('qp-access-token', 'qp-refresh-token')) as mock_create_token,
        ):
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            with (
                patch('api.oauth.get_conn', return_value=mock_conn),
                patch('api.oauth.Users') as mock_users,
            ):
                mock_users.return_value.get_user_row = AsyncMock(return_value={
                    'id': 42, 'admin': False, 'status': 'active', 'token_version': 0,
                })
                mock_users.return_value.get_user_role = AsyncMock(return_value=(
                    'radiologist', ['REPORT_READ', 'REPORT_WRITE'],
                ))
                from api.oauth import oauth_callback
                resp = await oauth_callback(request)

        assert resp.status_code == 200
        mock_exchange.assert_called_once()
        passed_provider = mock_exchange.call_args[0][2]
        assert passed_provider['client_secret'] == 'decrypted_secret'
        mock_create_token.assert_called_once()
        kwargs = mock_create_token.call_args[1]
        assert kwargs.get('token_version') == 0
        # Callback must mint from DB role/permissions, not provider default (R2-02).
        assert kwargs.get('role') == 'radiologist'
        assert kwargs.get('permissions') == ['REPORT_READ', 'REPORT_WRITE']

    @pytest.mark.asyncio
    async def test_callback_fails_when_db_provider_not_found(self):
        request = MagicMock()
        request.query_params = {'code': 'code', 'state': 'state'}

        with (
            patch('api.oauth._verify_state', AsyncMock(return_value=('verifier', 'missing-id', None))),
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
    """B2: role permission change increments token_version — exercised through
    the REAL RoleHandler.put decision path (api/roles.py) with a mocked conn,
    not by calling the mocked increment method directly (the old tests passed
    regardless of the handler's actual behavior)."""

    @staticmethod
    def _patch_conn():
        conn = MagicMock()
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetchval = AsyncMock(return_value=0)
        conn.execute = AsyncMock()
        return patch('api.roles.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ))

    @staticmethod
    def _patch_db_class(cls_name, **methods):
        cls_mock = MagicMock()
        instance = cls_mock.return_value
        for name, ret in methods.items():
            setattr(instance, name, AsyncMock(return_value=ret))
        return patch(f'api.roles.{cls_name}', cls_mock), cls_mock

    @staticmethod
    def _make_app(route, user):
        from starlette.exceptions import HTTPException

        from api.validate import _ValidationException, validation_exception_handler

        class _FakeAuth(BaseHTTPMiddleware):
            def __init__(self, app, user=None):
                super().__init__(app)
                self._user = user or User({'id': 1, 'permissions': []})

            async def dispatch(self, request, call_next):
                request.scope['user'] = self._user
                request.scope['auth'] = None
                return await call_next(request)

        return Starlette(
            routes=[route],
            middleware=[Middleware(_FakeAuth, user=user)],
            exception_handlers={
                HTTPException: lambda request, exc: JSONResponse(
                    {'error': exc.detail}, status_code=exc.status_code
                ),
                _ValidationException: validation_exception_handler,
            },
        )

    def test_role_patch_with_permissions_calls_bulk_increment(self):
        from api.roles import RoleHandler

        role = {'id': 'r1', 'name': 'X', 'slug': 'x', 'built_in': False}
        route = Route('/api/roles/{id}', endpoint=RoleHandler)
        p_roles = self._patch_db_class('Roles', get=role, patch=None)
        p_users = self._patch_db_class('Users', bulk_increment_token_version_by_role=None)
        p_audit = self._patch_db_class('AuditLog', log_event=None)

        with self._patch_conn(), p_roles[0] as roles_cls, p_users[0] as users_cls, p_audit[0]:
            with TestClient(self._make_app(route, User({'id': 1, 'admin': True, 'permissions': ['*']}))) as client:
                resp = client.put('/api/roles/r1', json={'permissions': ['FILE_READ']})

        assert resp.status_code == 200, resp.text
        # The real handler patched the role first, then bumped token_version
        # for every user holding it (api/roles.py `if body.permissions ...`).
        roles_cls.return_value.patch.assert_awaited_once()
        users_cls.return_value.bulk_increment_token_version_by_role.assert_awaited_once_with('r1')

    def test_role_patch_without_permissions_skips_bulk(self):
        from api.roles import RoleHandler

        role = {'id': 'r1', 'name': 'X', 'slug': 'x', 'built_in': False}
        route = Route('/api/roles/{id}', endpoint=RoleHandler)
        p_roles = self._patch_db_class('Roles', get=role, patch=None)
        p_users = self._patch_db_class('Users', bulk_increment_token_version_by_role=None)
        p_audit = self._patch_db_class('AuditLog', log_event=None)

        with self._patch_conn(), p_roles[0] as roles_cls, p_users[0] as users_cls, p_audit[0]:
            with TestClient(self._make_app(route, User({'id': 1, 'admin': True, 'permissions': ['*']}))) as client:
                # A rename carries no permissions payload — the handler must
                # NOT bump token_version (a no-op bump would force every
                # holder to re-login for nothing).
                resp = client.put('/api/roles/r1', json={'name': 'Renamed'})

        assert resp.status_code == 200, resp.text
        roles_cls.return_value.patch.assert_awaited_once()
        users_cls.return_value.bulk_increment_token_version_by_role.assert_not_awaited()
