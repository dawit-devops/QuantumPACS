import json
import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import block_token, create_token, is_blocked
from api.users import ChangePassword, Logout, RevokeToken
from api.validate import validation_exception_handler, _ValidationException

SECRET = 'test-secret-key-for-blocklist-tests!!'


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def _fake_auth_middleware(user):
    class FakeAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.scope['user'] = user
            request.scope['auth'] = None
            return await call_next(request)

    return Middleware(FakeAuth)


class TestLogout:
    def _make_app(self):
        return Starlette(
            routes=[Route('/api/auth/logout', endpoint=Logout)],
        )

    def test_logout_blocklists_token(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout', headers={'X-Auth-Pacs': token})

        assert resp.status_code == 200
        assert resp.json() == {'message': 'Logged out'}
        mock_block.assert_awaited_once_with(token)

    def test_logout_without_token(self):
        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout')

        assert resp.status_code == 200
        mock_block.assert_not_awaited()

    def test_logout_with_bearer_token(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)

    def test_logout_with_cookie(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': False})

        client = TestClient(self._make_app())
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            client.cookies['token'] = token
            resp = client.post('/api/auth/logout')

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)


class TestChangePasswordBlocklist:
    @pytest.fixture(autouse=True)
    def _hermetic_password_bucket(self):
        # Redis is up in the dev env; the password bucket would persist this
        # test's attempts in the shared zset and 429 subsequent runs. Force
        # the in-memory fallback so the tests stay deterministic.
        with patch('api.ratelimit._get_rate_redis',
                   new=AsyncMock(return_value=None)):
            yield

    def _make_app(self, user):
        return Starlette(
            routes=[Route('/api/change_password', endpoint=ChangePassword)],
            middleware=[_fake_auth_middleware(user)],
        )

    def test_change_password_blocklists_token(self):
        user = User({'id': 1, 'admin': True})
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app(user))

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.users.block_token', new=AsyncMock()) as mock_block,
            patch('api.users.Users') as mock_users,
        ):
            mock_users.return_value.change_password = AsyncMock(return_value=True)
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            with patch('api.users.get_conn', return_value=mock_conn):
                resp = client.post(
                    '/api/change_password',
                    json={'new_password': 'newpassword123', 'current_password': 'oldpass'},
                    headers={'X-Auth-Pacs': token},
                )

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with(token)

    def test_change_password_skip_blocklist_on_failure(self):
        user = User({'id': 1, 'admin': True})
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        client = TestClient(self._make_app(user))
        from exceptions import ApiException

        with (
            patch('api.tokens.config', {'secret': SECRET}),
            patch('api.users.block_token', new=AsyncMock()) as mock_block,
            patch('api.users.Users') as mock_users,
        ):
            mock_users.return_value.change_password = AsyncMock(
                side_effect=ApiException('Password error')
            )
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            with patch('api.users.get_conn', return_value=mock_conn):
                resp = client.post(
                    '/api/change_password',
                    json={'new_password': 'validpassword', 'current_password': 'oldpass'},
                    headers={'X-Auth-Pacs': token},
                )

        assert resp.status_code == 400
        mock_block.assert_not_awaited()


class TestRevokeToken:
    def _make_app(self, user):
        return Starlette(
            routes=[Route('/api/auth/revoke', endpoint=RevokeToken)],
            middleware=[_fake_auth_middleware(user)],
        )

    def test_revoke_requires_admin(self):
        user = User({'id': 2, 'admin': False})
        client = TestClient(self._make_app(user))
        resp = client.post(
            '/api/auth/revoke',
            json={'token': 'some-jti'},
        )
        assert resp.status_code == 403

    def test_revoke_blocklists_provided_token(self):
        user = User({'id': 1, 'admin': True, 'permissions': ['USER_ADMIN']})
        client = TestClient(self._make_app(user))
        with patch('api.users.block_token', new=AsyncMock()) as mock_block:
            resp = client.post(
                '/api/auth/revoke',
                json={'token': 'user-jwt-to-revoke'},
            )

        assert resp.status_code == 200
        mock_block.assert_awaited_once_with('user-jwt-to-revoke')

    def test_revoke_returns_422_without_token_field(self):
        user = User({'id': 1, 'admin': True, 'permissions': ['USER_ADMIN']})
        app = Starlette(
            routes=[Route('/api/auth/revoke', endpoint=RevokeToken)],
            middleware=[_fake_auth_middleware(user)],
            exception_handlers={_ValidationException: validation_exception_handler},
        )
        client = TestClient(app)
        resp = client.post('/api/auth/revoke', json={})
        assert resp.status_code == 422


class TestBlockedTokenAuth:
    """Integration: a blocked token is rejected on subsequent requests."""

    def _make_app(self):
        app = Starlette(
            routes=[
                Route('/api/protected', endpoint=self._protected),
            ],
        )
        return app

    async def _protected(self, request):
        return JSONResponse({'ok': True})

    def test_blocked_token_returns_401(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})

        from starlette.middleware.authentication import AuthenticationMiddleware
        from api.auth import TokenAuth

        with patch('api.auth.config', {'secret': SECRET, 'cors_origins': '*'}):
            app = Starlette(
                routes=[
                    Route('/api/protected', endpoint=self._protected),
                ],
                middleware=[
                    Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                               on_error=TokenAuth.on_auth_error),
                ],
            )

            with patch('api.tokens.is_blocked', new=AsyncMock(return_value=True)):
                client = TestClient(app)
                resp = client.get('/api/protected', headers={'X-Auth-Pacs': token})

            assert resp.status_code == 401


class TestBlocklistFailOpenSignal:
    """R2-07: the blocklist is fail-open by design (auth never 503s when
    Redis is down), but the degradation must be loud — throttled ERROR logs
    and a dedicated degraded component in /api/health."""

    def setup_method(self):
        from api import tokens
        tokens.reset_blocklist_warn()
        tokens._blocklist_redis = None

    def test_is_blocked_fails_open_without_redis(self, caplog):
        import logging
        from api import tokens
        with (
            patch('api.tokens._get_blocklist_redis',
                  new=AsyncMock(return_value=None)),
            caplog.at_level(logging.ERROR, logger='api.tokens'),
        ):
            assert _run(tokens.is_blocked('jti-1')) is False
        assert 'Token blocklist unavailable' in caplog.text
        assert 'fail-open' in caplog.text

    def test_is_blocked_fails_open_on_redis_error(self, caplog):
        import logging
        from api import tokens
        r = AsyncMock()
        r.exists.side_effect = Exception('connection refused')
        with (
            patch('api.tokens._get_blocklist_redis', new=AsyncMock(return_value=r)),
            caplog.at_level(logging.ERROR, logger='api.tokens'),
        ):
            assert _run(tokens.is_blocked('jti-2')) is False
        assert 'Token blocklist unavailable' in caplog.text

    def test_block_token_fails_open_and_logs_error(self, caplog):
        import logging
        from api import tokens
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        with (
            patch('api.tokens._get_blocklist_redis',
                  new=AsyncMock(return_value=None)),
            caplog.at_level(logging.ERROR, logger='api.tokens'),
        ):
            _run(tokens.block_token(token))
        assert 'Token blocklist unavailable' in caplog.text

    def test_warning_is_throttled(self, caplog):
        import logging
        from api import tokens
        with (
            patch('api.tokens._get_blocklist_redis',
                  new=AsyncMock(return_value=None)),
            caplog.at_level(logging.ERROR, logger='api.tokens'),
        ):
            assert _run(tokens.is_blocked('jti-3')) is False
            assert _run(tokens.is_blocked('jti-4')) is False
            assert _run(tokens.is_blocked('jti-5')) is False
        assert caplog.text.count('Token blocklist unavailable') == 1


class TestBlocklistHealthSignal:
    def test_blocklist_component_degraded_without_redis(self):
        from api import telemetry
        with patch('api.redis_client.is_available', return_value=False):
            result = _run(telemetry._check_token_blocklist())
        assert result['status'] == 'degraded'
        assert 'fail-open' in result['message']

    def test_health_endpoint_reports_blocklist_without_503(self):
        from api import telemetry
        ok = {'status': 'ok', 'latency_ms': 1}
        probes = {
            '_check_db': AsyncMock(return_value=ok),
            '_check_es': AsyncMock(return_value=ok),
            '_check_redis': AsyncMock(return_value=ok),
            '_check_storage': AsyncMock(return_value=ok),
            '_check_dicom_listener': AsyncMock(return_value=ok),
            '_check_ingestion_service': AsyncMock(return_value=ok),
            '_check_hl7_listener': AsyncMock(return_value=ok),
            '_check_fhir': AsyncMock(return_value=ok),
            '_check_auth': AsyncMock(return_value=ok),
            '_check_token_blocklist': AsyncMock(return_value={
                'status': 'degraded', 'latency_ms': 0,
                'message': 'Token blocklist fail-open active'},
            ),
        }
        with ExitStack() as stack:
            for name, mock in probes.items():
                stack.enter_context(patch(f'api.telemetry.{name}', new=mock))
            resp = _run(telemetry.health_endpoint(None))
        data = json.loads(resp.body)
        assert resp.status_code == 200
        assert data['status'] == 'degraded'
        assert data['components']['token_blocklist']['status'] == 'degraded'

    def test_health_endpoint_blocklist_ok_when_redis_up(self):
        from api import telemetry
        ok = {'status': 'ok', 'latency_ms': 1}
        probes = {f'_check_{name}': AsyncMock(return_value=ok)
                  for name in ('db', 'es', 'redis', 'storage',
                               'dicom_listener', 'ingestion_service',
                               'hl7_listener', 'fhir', 'auth')}
        probes['_check_token_blocklist'] = AsyncMock(return_value=ok)
        with ExitStack() as stack:
            for name, mock in probes.items():
                stack.enter_context(patch(f'api.telemetry.{name}', new=mock))
            resp = _run(telemetry.health_endpoint(None))
        data = json.loads(resp.body)
        assert resp.status_code == 200
        assert data['status'] == 'ok'
        assert data['components']['token_blocklist']['status'] == 'ok'


class TestLocalDenylistOverlay:
    """R2-H4: revocation survives a Redis outage via the bounded in-process
    overlay. The overlay is authoritative for recently revoked tokens even
    when the primary Redis blocklist is unreachable."""

    def setup_method(self):
        from api.tokens import reset_local_denylist
        reset_local_denylist()

    def _jti(self, token):
        import jwt as pyjwt

        from api.jwt_keys import get_public_key_pem

        return pyjwt.decode(
            token, get_public_key_pem(), algorithms=['RS256'],
            options={'verify_aud': False, 'verify_exp': False},
        )['jti']

    def test_blocked_token_rejected_without_redis(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        jti = self._jti(token)
        with patch('api.tokens._get_blocklist_redis', new=AsyncMock(return_value=None)):
            _run(block_token(token))
            assert _run(is_blocked(jti)) is True

    def test_revocation_survives_redis_outage(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True})
        jti = self._jti(token)
        # Block with a healthy redis first.
        fake_redis = AsyncMock()
        with patch('api.tokens._get_blocklist_redis',
                   new=AsyncMock(return_value=fake_redis)):
            _run(block_token(token))
        fake_redis.set.assert_awaited()
        # Then redis dies — the token must still be rejected via the overlay.
        with patch('api.tokens._get_blocklist_redis', new=AsyncMock(return_value=None)):
            assert _run(is_blocked(jti)) is True

    def test_expired_token_not_added_to_overlay(self):
        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True}, expire={'seconds': -5})
        jti = self._jti(token)
        with patch('api.tokens._get_blocklist_redis', new=AsyncMock(return_value=None)):
            _run(block_token(token))
            assert _run(is_blocked(jti)) is False

    def test_overlay_purges_expired_entries(self):
        from api import tokens as tokens_mod

        with patch('api.tokens.config', {'secret': SECRET}):
            token = create_token({'id': 1, 'admin': True}, expire={'seconds': -5})
        jti = self._jti(token)
        tokens_mod._local_denylist[jti] = 0.0
        assert _run(is_blocked(jti)) is False
        assert jti not in tokens_mod._local_denylist
