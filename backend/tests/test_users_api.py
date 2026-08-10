"""API-level tests for /api/users: pagination clamping and the
deactivate last-active-admin guard (production hardening)."""
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.users import UsersHandler, UsersDeactivate, Login
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['USER_READ', 'USER_DELETE']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=None)
    return conn


class TestUsersHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/users', endpoint=UsersHandler)], user)

    def test_list_clamps_large_limit_and_negative_offset(self):
        mock_conn = _mock_conn()
        mock_users = MagicMock()
        mock_users.get_users = AsyncMock(return_value=[])
        mock_users.count_users = AsyncMock(return_value=0)
        with (
            patch('api.users.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.users.Users', return_value=mock_users),
        ):
            client = TestClient(self._make_app())
            resp = client.get('/users?limit=99999&offset=-5')
        assert resp.status_code == 200
        mock_users.get_users.assert_awaited_once()
        args = mock_users.get_users.await_args.kwargs
        assert args['limit'] == 200
        assert args['offset'] == 0

    def test_list_accepts_normal_params_unchanged(self):
        mock_conn = _mock_conn()
        mock_users = MagicMock()
        mock_users.get_users = AsyncMock(return_value=[])
        mock_users.count_users = AsyncMock(return_value=0)
        with (
            patch('api.users.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.users.Users', return_value=mock_users),
        ):
            client = TestClient(self._make_app())
            resp = client.get('/users?limit=20&offset=40')
        assert resp.status_code == 200
        args = mock_users.get_users.await_args.kwargs
        assert args['limit'] == 20
        assert args['offset'] == 40


class TestUsersDeactivate:
    def _make_app(self, user=None):
        return _make_app([Route('/users/deactivate', endpoint=UsersDeactivate)], user)

    def _patch_deps(self, mock_conn, deactivate_side_effect=None):
        mock_users = MagicMock()
        mock_users.deactivate = AsyncMock(side_effect=deactivate_side_effect)
        mock_audit = MagicMock()
        mock_audit.log_event = AsyncMock()
        return (
            patch('api.users.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.users.Users', return_value=mock_users),
            patch('api.users.AuditLog', return_value=mock_audit),
            mock_users,
        )

    def test_deactivate_success(self):
        mock_conn = _mock_conn()
        p1, p2, p3, _ = self._patch_deps(mock_conn)
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post('/users/deactivate', json={'id': 5})
        assert resp.status_code == 200

    def test_deactivate_last_admin_returns_403(self):
        from exceptions import ApiException
        mock_conn = _mock_conn()
        p1, p2, p3, _ = self._patch_deps(
            mock_conn,
            deactivate_side_effect=ApiException('Cannot deactivate the last active admin'),
        )
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post('/users/deactivate', json={'id': 1})
        assert resp.status_code == 403
        assert 'last active admin' in resp.json()['error']['message']

    def test_deactivate_unknown_user_returns_403(self):
        from exceptions import ApiException
        mock_conn = _mock_conn()
        p1, p2, p3, _ = self._patch_deps(
            mock_conn,
            deactivate_side_effect=ApiException('User not found'),
        )
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post('/users/deactivate', json={'id': 999})
        assert resp.status_code == 403
        assert resp.json()['error']['message'] == 'User not found'


class TestLoginResponse:
    """R2-LOW: the password-login response must not carry the refresh token
    in the JSON body — it is delivered only as an HttpOnly cookie."""

    def _make_app(self):
        return _make_app([Route('/login', endpoint=Login)])

    def test_login_body_has_no_refresh_token(self):
        mock_conn = _mock_conn()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.login = AsyncMock(return_value={
            'id': 7, 'admin': False, 'tenant': 'hospital-a',
        })
        mock_users.return_value.update_last_login = AsyncMock()
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'receptionist', ['REGISTRATION_READ'],
        ))
        mock_users.return_value.get_token_version = AsyncMock(return_value=0)

        with (
            patch('api.users.Users', mock_users),
            patch('api.users.get_conn', return_value=mock_conn),
            patch('api.users.login_bucket') as mock_bucket,
            patch('api.ratelimit._get_rate_redis', new=AsyncMock(return_value=None)),
        ):
            mock_bucket.check = AsyncMock(return_value=(True, ''))
            mock_bucket.record_db = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            client = TestClient(self._make_app())
            resp = client.post('/login', json={'username': 'u', 'password': 'pw'})

        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert 'refresh_token' not in data
        set_cookie = resp.headers.get('set-cookie', '')
        assert 'refresh_token=' in set_cookie
        assert 'HttpOnly' in set_cookie
