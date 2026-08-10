from unittest.mock import AsyncMock, MagicMock, patch

import json

import pytest

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from api.oauth import (
    _code_verifier, _code_challenge, oauth_login, oauth_callback, oidc_discovery,
    oidc_jwks, oauth_token_exchange,
)


class TestOidcDiscovery:
    def test_discovery_returns_valid_config(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        assert resp.status_code == 200
        data = resp.json()

        assert data['issuer'].endswith('/api')
        assert 'authorization_endpoint' in data
        assert 'token_endpoint' in data
        assert 'jwks_uri' in data
        assert 'code' in data['response_types_supported']
        assert 'S256' in data['code_challenge_methods_supported']
        assert 'authorization_code' in data['grant_types_supported']
        # Only RS256 is advertised: the JWKS endpoint publishes the RSA key,
        # the legacy HS256 secret signs nothing advertised here.
        assert data['id_token_signing_alg_values_supported'] == ['RS256']

    def test_discovery_endpoints_contain_base_url(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        data = resp.json()
        assert '/api/oauth/login' in data['authorization_endpoint']
        assert '/api/oauth/token' in data['token_endpoint']
        assert '/api/oauth/jwks' in data['jwks_uri']

    def test_discovery_includes_required_claims(self):
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        resp = client.get('/api/.well-known/openid-configuration')

        claims = resp.json()['claims_supported']
        for claim in ('sub', 'iss', 'aud', 'exp', 'iat'):
            assert claim in claims

    def test_discovery_uses_configured_token_issuer(self):
        # R2-M5: the advertised issuer is config-derived — the same key that
        # mints the JWT iss claim. Pinned → discovery matches minted tokens.
        app = Starlette(routes=[Route('/api/.well-known/openid-configuration', endpoint=oidc_discovery)])
        client = TestClient(app)
        with patch('api.oauth.config', {'token_issuer': 'https://pacs.example.com/api'}):
            resp = client.get('/api/.well-known/openid-configuration')

        assert resp.json()['issuer'] == 'https://pacs.example.com/api'


class TestOAuthUtils:
    def test_code_verifier_length(self):
        v = _code_verifier()
        assert len(v) >= 43
        assert len(v) <= 128

    def test_code_challenge_deterministic(self):
        v = _code_verifier()
        c1 = _code_challenge(v)
        c2 = _code_challenge(v)
        assert c1 == c2

    def test_code_challenge_differs_for_diff_verifiers(self):
        v1 = _code_verifier()
        v2 = _code_verifier()
        assert _code_challenge(v1) != _code_challenge(v2)


class TestOidcJwks:
    def test_jwks_endpoint_publishes_rsa_key(self):
        app = Starlette(routes=[Route('/api/oauth/jwks', endpoint=oidc_jwks)])
        client = TestClient(app)
        resp = client.get('/api/oauth/jwks')

        assert resp.status_code == 200
        keys = resp.json()['keys']
        assert len(keys) == 1
        key = keys[0]
        assert key['kty'] == 'RSA'
        assert key['use'] == 'sig'
        assert key['alg'] == 'RS256'
        assert key['kid']
        assert key['n']
        assert key['e'] == 'AQAB'

    def test_minted_tokens_verify_with_jwks_key(self):
        import jwt as pyjwt

        from api.jwt_keys import get_kid, get_public_key_pem
        from api.tokens import create_token

        with patch('api.tokens.config', {'secret': 'jwt-test-secret'}):
            token = create_token({'id': 1, 'admin': True}, expire={'minutes': 60})

        header = pyjwt.get_unverified_header(token)
        assert header['alg'] == 'RS256'
        assert header['kid'] == get_kid()

        payload = pyjwt.decode(
            token, get_public_key_pem(), algorithms=['RS256'],
            options={'verify_aud': False},
        )
        assert payload['id'] == 1

    def test_legacy_hs256_token_still_verifies_during_rotation(self):
        import time

        import jwt as pyjwt

        from api.tokens import verify_token

        with patch('api.tokens.config', {'secret': 'jwt-test-secret'}):
            legacy = pyjwt.encode(
                {'id': 1, 'admin': True, 'exp': int(time.time()) + 3600},
                'jwt-test-secret', algorithm='HS256',
            )
            payload = verify_token(legacy)

        assert payload['id'] == 1

    def test_jwks_is_reachable_without_auth(self):
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware

        from api.auth import TokenAuth

        app = Starlette(
            routes=[Route('/api/oauth/jwks', endpoint=oidc_jwks)],
            middleware=[
                Middleware(
                    AuthenticationMiddleware, backend=TokenAuth(),
                    on_error=TokenAuth.on_auth_error,
                ),
            ],
        )
        client = TestClient(app)

        resp = client.get('/api/oauth/jwks')
        assert resp.status_code == 200
        assert resp.json()['keys'][0]['alg'] == 'RS256'


class TestOAuthLogin:
    @pytest.mark.asyncio
    async def test_login_redirects_when_configured(self):
        request = MagicMock()
        request.query_params = {}
        cfg = {
            'oauth_issuer': 'https://accounts.google.com',
            'oauth_client_id': 'my-client-id',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_scope': 'openid email profile',
        }
        with patch('api.oauth.config', cfg):
            with patch('api.oauth._store_state', AsyncMock()):
                resp = await oauth_login(request)
        assert resp.status_code == 302
        location = resp.headers.get('location', '')
        assert 'accounts.google.com' in location
        assert 'response_type=code' in location
        assert 'code_challenge' in location

    @pytest.mark.asyncio
    async def test_login_returns_501_when_not_configured(self):
        request = MagicMock()
        request.query_params = {}
        cfg = {'oauth_issuer': '', 'oauth_client_id': ''}
        with patch('api.oauth.config', cfg):
            resp = await oauth_login(request)
        assert resp.status_code == 501


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_callback_with_error_returns_401(self):
        request = MagicMock()
        request.query_params = {'error': 'access_denied'}
        resp = await oauth_callback(request)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_400(self):
        request = MagicMock()
        request.query_params = {}
        resp = await oauth_callback(request)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_401(self):
        request = MagicMock()
        request.query_params = {'code': 'abc', 'state': 'bad'}
        with patch('api.oauth._verify_state', AsyncMock(return_value=(None, None, None))):
            resp = await oauth_callback(request)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_callback_full_flow(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
            'oauth_default_role': 'radiologist',
        }

        tokens = {'id_token': 'fake-id-token'}
        claims = MockClaims(sub='oauth-user-1', email='dr@example.com', name='Dr Smith')

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.get_user_row = AsyncMock(return_value={
            'id': 42, 'admin': False, 'status': 'active', 'token_version': 0,
        })
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'radiologist', ['REPORT_READ'],
        ))

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None, None))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        with patch('api.oauth._find_or_create_user', AsyncMock(return_value={
                            'id': 42, 'admin': False, 'username': 'dr',
                        })):
                            with patch('api.oauth.get_conn', return_value=mock_conn):
                                with patch('api.oauth.Users', mock_users):
                                    with patch(
                                        'api.oauth.create_token_pair',
                                        return_value=('qp-access-jwt', 'qp-refresh-jwt'),
                                    ) as mock_create_pair:
                                        resp = await oauth_callback(request)

        assert resp.status_code == 200
        body = resp.body
        assert b'qp-access-jwt' in body
        # R2-LOW: the refresh token must NOT ride in the JSON body — it is
        # delivered only as an HttpOnly cookie.
        assert b'qp-refresh-jwt' not in body
        assert b'token' in body
        set_cookies = [v.decode() for k, v in resp.raw_headers if k == b'set-cookie']
        assert any(c.startswith('refresh_token=qp-refresh-jwt') for c in set_cookies)
        assert all('HttpOnly' in c for c in set_cookies)
        assert any('Path=/api/auth' in c for c in set_cookies)
        kwargs = mock_create_pair.call_args[0][0]
        assert kwargs.get('id') == 42
        mock_create_pair.assert_called_once()
        assert mock_create_pair.call_args.kwargs.get('role') == 'radiologist'
        assert mock_create_pair.call_args.kwargs.get('permissions') == ['REPORT_READ']

    @pytest.mark.asyncio
    async def test_callback_refuses_provisioning_when_auto_provision_disabled(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
        }
        tokens = {'id_token': 'fake-id-token'}
        claims = MockClaims(sub='oauth-user-1', email='dr@example.com', name='Dr Smith')

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None, None))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        # Provider rows are plain dicts here: auto_provision=False
                        # arrives from the DB-configured provider path.
                        with patch(
                            'api.oauth._find_or_create_user',
                            AsyncMock(return_value=None),
                        ):
                            resp = await oauth_callback(request)

        assert resp.status_code == 403
        body = resp.body
        assert b'ACCOUNT_NOT_PROVISIONED' in body

    @pytest.mark.asyncio
    async def test_callback_rejects_disabled_provider(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        with patch(
            'api.oauth._verify_state',
            AsyncMock(return_value=('code-verifier', 'provider-id', None)),
        ):
            with patch(
                'api.oauth._get_provider_by_id',
                AsyncMock(return_value={'enabled': False}),
            ):
                resp = await oauth_callback(request)

        assert resp.status_code == 403
        assert b'PROVIDER_DISABLED' in resp.body

    @pytest.mark.asyncio
    async def test_callback_rejects_nonce_mismatch(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        class NonceMismatchClaims(MockClaims):
            def get(self, key, default=None):
                if key == 'nonce':
                    return 'attacker-forged-nonce'
                return super().get(key, default)

        tokens = {'id_token': 'fake-id-token'}
        claims = NonceMismatchClaims(sub='oauth-user-1', email='dr@example.com')
        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
        }

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None, 'real-nonce'))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        resp = await oauth_callback(request)

        assert resp.status_code == 401
        assert b'NONCE_MISMATCH' in resp.body


class TestOAuthTokenExchange:
    @pytest.fixture(autouse=True)
    def _hermetic_rate_limit(self):
        # Token grants are rate-limited per-IP (R2-M9); the module-global
        # in-memory fallback would accumulate across runs on the shared dev
        # host. A fresh bucket per test keeps the suite deterministic.
        from api.ratelimit import RedisTokenBucket
        with (
            patch('api.ratelimit.refresh_bucket',
                  RedisTokenBucket(max_attempts=30, window_seconds=60)),
            patch('api.ratelimit._get_rate_redis', AsyncMock(return_value=None)),
        ):
            yield

    def test_empty_body_returns_unsupported_grant(self):
        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        resp = client.post('/api/oauth/token', json={})

        assert resp.status_code == 400
        data = resp.json()
        assert data['error']['code'] == 'UNSUPPORTED_GRANT'

    def test_malformed_json_returns_400(self):
        # R2-M6: raw request.json() used to 500 on malformed bodies; the
        # capped body read turns them into a clean 400.
        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        resp = client.post('/api/oauth/token', content=b'{not json', headers={
            'Content-Type': 'application/json',
        })

        assert resp.status_code == 400
        assert resp.json()['error']['code'] == 'INVALID_JSON'

    def test_oversized_body_returns_413(self):
        # R2-M6: bodies above the 1MB cap are refused before buffering.
        from api.validate import MAX_BODY_BYTES

        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        resp = client.post('/api/oauth/token', content=b'x' * (MAX_BODY_BYTES + 1), headers={
            'Content-Type': 'application/json',
        })

        assert resp.status_code == 413
        assert resp.json()['error']['code'] == 'BODY_TOO_LARGE'

    def test_json_array_body_returns_400(self):
        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        resp = client.post('/api/oauth/token', content=b'[1,2,3]', headers={
            'Content-Type': 'application/json',
        })

        assert resp.status_code == 400
        assert resp.json()['error']['code'] == 'INVALID_JSON'

    def test_refresh_grant_delivers_refresh_token_only_as_cookie(self):
        # R2-LOW: refresh_token leaves the JSON body; the rotating credential
        # arrives via an HttpOnly cookie scoped to /api.
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.get_user_row = AsyncMock(return_value={
            'id': 7, 'admin': False, 'status': 'active', 'token_version': 0,
            'tenant': 'hospital-a',
        })
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'receptionist', ['REGISTRATION_READ'],
        ))

        app = Starlette(routes=[Route('/api/oauth/token', endpoint=oauth_token_exchange, methods=['POST'])])
        client = TestClient(app)
        with (
            patch('api.oauth.verify_refresh_token', return_value={
                'jti': 'jti-1', 'id': 7, 'type': 'refresh',
                'token_version': 0, 'tenant': 'hospital-a',
            }),
            patch('api.oauth.is_blocked', new=AsyncMock(return_value=False)),
            patch('api.oauth.block_token', new=AsyncMock()),
            patch('api.oauth.get_conn', return_value=mock_conn),
            patch('api.oauth.Users', mock_users),
            patch('api.oauth.create_token_pair',
                  return_value=('new-access', 'new-refresh')),
        ):
            resp = client.post('/api/oauth/token', json={
                'grant_type': 'refresh_token',
                'refresh_token': 'the-old-refresh-jwt',
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data['access_token'] == 'new-access'
        assert 'refresh_token' not in data
        set_cookie = resp.headers.get('set-cookie', '')
        assert 'refresh_token=new-refresh' in set_cookie
        assert 'HttpOnly' in set_cookie
        assert 'SameSite=strict' in set_cookie
        assert 'Path=/api' in set_cookie


class TestOAuthCallbackTenantClaim:
    """NEW-MEDIUM (round-2 audit): the SSO callback must carry the tenant
    claim in minted tokens exactly like the password-login path — otherwise
    the tenancy gate treats SSO sessions as unscoped."""

    @pytest.mark.asyncio
    async def test_callback_token_user_includes_tenant(self):
        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}

        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
        }
        tokens = {'id_token': 'fake-id-token'}
        claims = MockClaims(sub='oauth-user-1', email='dr@example.com', name='Dr Smith')

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.get_user_row = AsyncMock(return_value={
            'id': 42, 'admin': False, 'status': 'active', 'token_version': 0,
            'tenant': 'hospital-a',
        })
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'radiologist', ['REPORT_READ'],
        ))

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None, None))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        with patch('api.oauth._find_or_create_user', AsyncMock(return_value={
                            'id': 42, 'admin': False, 'username': 'dr',
                        })):
                            with patch('api.oauth.get_conn', return_value=mock_conn):
                                with patch('api.oauth.Users', mock_users):
                                    with patch(
                                        'api.oauth.create_token_pair',
                                        return_value=('qp-access-jwt', 'qp-refresh-jwt'),
                                    ) as mock_create_pair:
                                        await oauth_callback(request)

        token_user = mock_create_pair.call_args[0][0]
        assert token_user['tenant'] == 'hospital-a'
        assert token_user['id'] == 42

    @pytest.mark.asyncio
    async def test_callback_minted_token_verifies_with_tenant_claim(self):
        # Stronger variant: run the REAL create_token_pair and verify the
        # tenant claim is actually in the JWT payload.
        import jwt as pyjwt

        from api.jwt_keys import get_public_key_pem
        from api.tokens import create_token_pair as real_create_token_pair

        request = MagicMock()
        request.query_params = {'code': 'valid-code', 'state': 'valid-state'}
        cfg = {
            'oauth_issuer': 'https://idp.example.com',
            'oauth_client_id': 'client-id',
            'oauth_client_secret': 'secret',
            'oauth_redirect_uri': 'http://localhost:8080/api/oauth/callback',
            'oauth_jwks_uri': 'https://idp.example.com/jwks',
            'oauth_token_url': 'https://idp.example.com/token',
        }
        tokens = {'id_token': 'fake-id-token'}
        claims = MockClaims(sub='oauth-user-1', email='dr@example.com')

        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.get_user_row = AsyncMock(return_value={
            'id': 42, 'admin': False, 'status': 'active', 'token_version': 0,
            'tenant': 'hospital-a',
        })
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'radiologist', ['REPORT_READ'],
        ))

        def _real_pair(user, **kwargs):
            return real_create_token_pair(user, **kwargs)

        with patch('api.oauth.config', cfg):
            with patch('api.oauth._verify_state', AsyncMock(return_value=('code-verifier', None, None))):
                with patch('api.oauth._exchange_code', AsyncMock(return_value=tokens)):
                    with patch('api.oauth._verify_id_token', return_value=claims):
                        with patch('api.oauth._find_or_create_user', AsyncMock(return_value={
                            'id': 42, 'admin': False, 'username': 'dr',
                        })):
                            with patch('api.oauth.get_conn', return_value=mock_conn):
                                with patch('api.oauth.Users', mock_users):
                                    with patch('api.oauth.create_token_pair', side_effect=_real_pair):
                                        resp = await oauth_callback(request)

        access = json.loads(resp.body)['access_token']
        payload = pyjwt.decode(
            access, get_public_key_pem(), algorithms=['RS256'],
            options={'verify_aud': False},
        )
        assert payload['tenant'] == 'hospital-a'
        assert payload['id'] == 42
        assert payload['role'] == 'radiologist'


class TestFindOrCreateUser:
    """R2-M7: group→role mapping on JIT provision and on login; tenant
    binding for tenant-scoped providers; no-groups_claim = unchanged."""

    def _conn(self, fetchrow=None, fetchval=None):
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow = AsyncMock(return_value=fetchrow)
        mock_conn.fetchval = AsyncMock(return_value=fetchval)
        mock_conn.execute = AsyncMock(return_value=None)
        return mock_conn

    def _provider(self, **overrides):
        provider = {
            'auto_provision': True,
            'default_role': 'patient',
            'groups_claim': 'groups',
            'groups_map': {'radiologists': 'radiologist',
                           'admins': 'platform_admin'},
            'tenant_id': None,
            'slug': 'idp',
        }
        provider.update(overrides)
        return provider

    def _claims_with_groups(self, groups):
        return MockClaims(
            sub='sub-1', email='u@example.com', name='U',
        )._with_groups(groups)

    @pytest.mark.asyncio
    async def test_jit_provision_uses_mapped_group_role(self):
        from api.oauth import _find_or_create_user

        mock_conn = self._conn(
            fetchrow=None,  # no existing identity
            fetchval='role-uuid-radiologist',  # role lookup for mapped slug
        )
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-1', 'u@example.com', 'U',
                self._provider(), self._claims_with_groups(['radiologists']),
            )

        assert user['id'] is not None
        assert user['role_id'] == 'role-uuid-radiologist'
        assert user['tenant'] is None

    @pytest.mark.asyncio
    async def test_jit_provision_falls_back_to_default_role_without_mapping(self):
        from api.oauth import _find_or_create_user

        mock_conn = self._conn(
            fetchrow=None,
            fetchval='role-uuid-patient',
        )
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-2', 'u2@example.com', 'U',
                self._provider(), None,  # no claims at all
            )

        assert user['role_id'] == 'role-uuid-patient'

    @pytest.mark.asyncio
    async def test_login_updates_role_from_groups(self):
        from api.oauth import _find_or_create_user

        existing = {
            'id': 9, 'role_id': None, 'username': 'u', 'admin': False,
            'oauth_sub': 'sub-1', 'email': 'u@example.com', 'tenant': None,
            'token_version': 0,
        }
        mock_conn = self._conn(
            fetchrow=existing,
            fetchval='role-uuid-radiologist',  # mapped slug lookup
        )
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-1', 'u@example.com', 'U',
                self._provider(), self._claims_with_groups(['radiologists']),
            )

        assert user['id'] == 9
        assert user['role_id'] == 'role-uuid-radiologist'
        mock_conn.execute.assert_awaited()
        # UPDATE ran against the mapped role id
        assert any('UPDATE users SET role_id' in str(c.args[0])
                   for c in mock_conn.execute.await_args_list)

    @pytest.mark.asyncio
    async def test_login_without_groups_claim_leaves_role_untouched(self):
        from api.oauth import _find_or_create_user

        existing = {
            'id': 9, 'role_id': 'existing-role', 'username': 'u', 'admin': False,
            'oauth_sub': 'sub-1', 'email': 'u@example.com', 'tenant': None,
            'token_version': 0,
        }
        mock_conn = self._conn(fetchrow=existing, fetchval=None)
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-1', 'u@example.com', 'U',
                self._provider(groups_claim=None, groups_map=None),
                self._claims_with_groups(['radiologists']),
            )

        assert user['role_id'] == 'existing-role'
        mock_conn.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_provision_binds_provider_tenant(self):
        from api.oauth import _find_or_create_user

        mock_conn = self._conn(
            fetchrow=None,
            fetchval='role-uuid-patient',
        )
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-3', 'u3@example.com', 'U',
                self._provider(tenant_id='hospital-a'), None,
            )

        assert user['tenant'] == 'hospital-a'
        # the INSERT must have included the tenant column
        inserts = [str(c.args[0]) for c in mock_conn.fetchval.await_args_list]
        assert any('"tenant"' in sql for sql in inserts)

    @pytest.mark.asyncio
    async def test_unmapped_group_falls_back_to_default_role(self):
        from api.oauth import _find_or_create_user

        mock_conn = self._conn(
            fetchrow=None,
            fetchval='role-uuid-patient',
        )
        with patch('api.oauth.get_conn', return_value=mock_conn):
            user = await _find_or_create_user(
                'sub-4', 'u4@example.com', 'U',
                self._provider(), self._claims_with_groups(['unknown-group']),
            )

        assert user['role_id'] == 'role-uuid-patient'


class MockClaims:
    """Shared claims stand-in that supports .get() and a groups extension."""

    def __init__(self, sub='user123', email='user@example.com', name='Test User'):
        self._data = {'sub': sub, 'email': email, 'name': name}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def _with_groups(self, groups):
        self._data['groups'] = groups
        return self
