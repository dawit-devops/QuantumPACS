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
from api.users import UsersBatchStatus, UsersHandler, UsersDeactivate, Login
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


def _patch_main_pool(mock_conn):
    """Login's tenant branch resolves registry rows on the MAIN pool via
    ``db.conn.get_database().acquire()`` — imported inside api.users, so the
    patch must target the db.conn.database global the accessor returns."""
    db_mock = MagicMock()
    db_mock.acquire.return_value = MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    )
    return patch('db.conn.database', db_mock)


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

    def test_list_scopes_tenant_scoped_admin_to_own_tenant(self):
        """P2-2 (tenant_admin review): a tenant-scoped non-admin holder of
        USER_READ sees only their own tenant's directory — the get_users call
        must carry tenant=<own>."""
        mock_conn = _mock_conn()
        mock_users = MagicMock()
        mock_users.get_users = AsyncMock(return_value=[])
        mock_users.count_users = AsyncMock(return_value=0)
        user = User({'id': 9, 'permissions': ['USER_READ'], 'tenant': 'default', 'admin': False})
        with (
            patch('api.users.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.users.Users', return_value=mock_users),
        ):
            client = TestClient(self._make_app(user=user))
            resp = client.get('/users')
        assert resp.status_code == 200
        assert mock_users.get_users.await_args.kwargs['tenant'] == 'default'
        assert mock_users.count_users.await_args.kwargs['tenant'] == 'default'

    def test_list_platform_admin_has_no_tenant_scope(self):
        """P2-2: super_admin / legacy admin keeps the full directory — the
        tenant filter must be None."""
        mock_conn = _mock_conn()
        mock_users = MagicMock()
        mock_users.get_users = AsyncMock(return_value=[])
        mock_users.count_users = AsyncMock(return_value=0)
        user = User({'id': 1, 'permissions': ['USER_READ'], 'admin': True})
        with (
            patch('api.users.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.users.Users', return_value=mock_users),
        ):
            client = TestClient(self._make_app(user=user))
            resp = client.get('/users')
        assert resp.status_code == 200
        assert mock_users.get_users.await_args.kwargs['tenant'] is None


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


class TestUsersBatchStatus:
    """ADM-02 bulk activate/deactivate (§2.10): one USER_DELETE-gated call
    drives many users through the SAME deactivate()/activate() primitives,
    so the last-active-admin lockout applies per id and failures are
    reported per id without aborting the batch."""

    def _make_app(self, user=None):
        return _make_app([Route('/users/batch-status', endpoint=UsersBatchStatus)], user)

    def _patch_deps(self, mock_conn, deactivate_side_effect=None):
        mock_users = MagicMock()
        mock_users.deactivate = AsyncMock(side_effect=deactivate_side_effect)
        mock_users.activate = AsyncMock()
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
            mock_audit,
        )

    def test_batch_deactivate_reports_changed_ids(self):
        mock_conn = _mock_conn()
        p1, p2, p3, users, audit = self._patch_deps(mock_conn)
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post(
                '/users/batch-status',
                json={'user_ids': [2, 3, 4], 'target_status': 'deactivated'},
            )
        assert resp.status_code == 200
        assert resp.json()['changed'] == [2, 3, 4]
        assert resp.json()['failed'] == []
        # The batch must reuse deactivate() (lockout guard + token bump),
        # not invent a second status-write path.
        assert users.deactivate.await_count == 3
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'user.batch_status_changed'

    def test_batch_activate_uses_activate_primitive(self):
        mock_conn = _mock_conn()
        p1, p2, p3, users, _ = self._patch_deps(mock_conn)
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post(
                '/users/batch-status',
                json={'user_ids': [7, 8], 'target_status': 'active'},
            )
        assert resp.status_code == 200
        assert resp.json()['changed'] == [7, 8]
        users.activate.assert_any_await(7)
        users.activate.assert_any_await(8)
        users.deactivate.assert_not_awaited()

    def test_batch_partial_failure_continues_and_reports(self):
        from exceptions import ApiException
        mock_conn = _mock_conn()
        p1, p2, p3, users, _ = self._patch_deps(mock_conn)
        # Second id hits the last-active-admin lockout; the rest proceed.
        users.deactivate = AsyncMock(
            side_effect=[None, ApiException('Cannot deactivate the last active admin'), None],
        )
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post(
                '/users/batch-status',
                json={'user_ids': [2, 3, 4], 'target_status': 'deactivated'},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data['changed'] == [2, 4]
        assert data['failed'] == [
            {'id': 3, 'error': 'Cannot deactivate the last active admin'},
        ]

    def test_batch_cannot_deactivate_own_account(self):
        mock_conn = _mock_conn()
        p1, p2, p3, users, _ = self._patch_deps(mock_conn)
        # _FakeAuth default user id is 1; requesting it for deactivation
        # would lock the operator out mid-session.
        with p1, p2, p3:
            client = TestClient(self._make_app())
            resp = client.post(
                '/users/batch-status',
                json={'user_ids': [1, 2], 'target_status': 'deactivated'},
            )
        assert resp.status_code == 403
        users.deactivate.assert_not_awaited()

    def test_batch_requires_user_delete_permission(self):
        mock_conn = _mock_conn()
        viewer = User({'id': 9, 'permissions': ['USER_READ', 'USER_WRITE']})
        p1, p2, p3, users, _ = self._patch_deps(mock_conn)
        with p1, p2, p3:
            client = TestClient(self._make_app(user=viewer))
            resp = client.post(
                '/users/batch-status',
                json={'user_ids': [2], 'target_status': 'deactivated'},
            )
        assert resp.status_code == 403
        users.deactivate.assert_not_awaited()

    def test_batch_rejects_empty_and_invalid_status(self):
        mock_conn = _mock_conn()
        p1, p2, p3, _, _ = self._patch_deps(mock_conn)
        with p1, p2, p3:
            client = TestClient(self._make_app())
            empty = client.post(
                '/users/batch-status', json={'user_ids': [], 'target_status': 'active'},
            )
            bad = client.post(
                '/users/batch-status', json={'user_ids': [2], 'target_status': 'paused'},
            )
        assert empty.status_code == 422
        assert bad.status_code == 422


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
            _patch_main_pool(mock_conn),
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

    def test_login_body_tenant_id_is_slug(self):
        # R2-16 regression: the login body's tenant_id is sent back by the
        # frontend as the X-Tenant-ID header, which TenantMiddleware resolves
        # via Tenants.get_by_slug(). Returning the DB UUID here 403'd every
        # tenant-scoped request after sign-in ("You do not have access to
        # this tenant").
        mock_conn = _mock_conn()
        mock_conn.__aenter__.return_value = mock_conn
        mock_users = MagicMock()
        mock_users.return_value.login = AsyncMock(return_value={
            'id': 7, 'admin': False, 'tenant': 'hospital-a',
        })
        mock_users.return_value.update_last_login = AsyncMock()
        mock_users.return_value.get_user_role = AsyncMock(return_value=(
            'radiologist', ['STUDY_READ'],
        ))
        mock_users.return_value.get_token_version = AsyncMock(return_value=0)

        with (
            patch('api.users.Users', mock_users),
            patch('api.users.get_conn', return_value=mock_conn),
            patch('api.users.login_bucket') as mock_bucket,
            patch('api.ratelimit._get_rate_redis', new=AsyncMock(return_value=None)),
            _patch_main_pool(mock_conn),
        ):
            mock_bucket.check = AsyncMock(return_value=(True, ''))
            mock_bucket.record_db = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                'id': 'uuid-1', 'name': 'Hospital A', 'slug': 'hospital-a',
            })
            client = TestClient(self._make_app())
            resp = client.post('/login', json={'username': 'u', 'password': 'pw'})

        data = resp.json()
        assert resp.status_code == 200
        assert data['tenant_id'] == 'hospital-a'
        assert data['tenant_name'] == 'Hospital A'
