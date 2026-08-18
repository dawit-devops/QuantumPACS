from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.notifications import NotificationPreferencesHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({
            'id': 42, 'permissions': ['FILE_READ'], 'role': 'super_admin',
        })

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(module, mock_conn):
    return patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(user=None):
    return Starlette(
        routes=[Route('/notifications/preferences', endpoint=NotificationPreferencesHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestNotificationPrefsApi:
    def test_get_returns_merged_prefs_with_role_defaults(self):
        """super_admin role default mutes clinical event types when no
        explicit row exists (the 49-item study.arrived flood from the review)."""
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'event_type': 'storage.quota_breach', 'enabled': True},
        ])
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(_make_app())
            resp = client.get('/notifications/preferences')
        assert resp.status_code == 200
        body = resp.json()
        assert body['preferences']['study.arrived'] is False
        assert body['preferences']['storage.quota_breach'] is True
        assert body['explicit'] == {'storage.quota_breach': True}

    def test_put_upserts_prefs_and_audits(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(_make_app())
            resp = client.put('/notifications/preferences', json={
                'preferences': {'study.arrived': True, 'system.alert': True},
            })
        assert resp.status_code == 200
        assert resp.json()['updated'] == ['study.arrived', 'system.alert']
        # one execute per pref + audit insert
        assert mock_conn.execute.await_count >= 3

    def test_put_rejects_unknown_event_type(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.notifications', mock_conn):
            client = TestClient(_make_app())
            resp = client.put('/notifications/preferences', json={
                'preferences': {'not.a.real.event': True},
            })
        assert resp.status_code == 422
        assert mock_conn.execute.await_count == 0

    def test_missing_permission(self):
        user = User({'id': 42, 'permissions': [], 'role': 'super_admin'})
        client = TestClient(_make_app(user=user))
        resp = client.get('/notifications/preferences')
        assert resp.status_code == 403


class TestNotifyFanoutGating:
    async def test_notify_role_skips_muted_users(self):
        """A user with an explicit disabled row gets nothing even for an ops
        event; the super_admin role default mutes clinical events."""
        from api.notify import notify_role
        conn = _mock_conn()
        conn.fetchrow = AsyncMock(return_value={'id': 1})
        conn.fetch = AsyncMock(side_effect=[
            [{'id': 5}, {'id': 6}],  # users with the role
            [{'user_id': 6, 'event_type': 'study.arrived', 'enabled': False}],
        ])
        with patch('api.notify.Notifications') as n_cls:
            n = MagicMock()
            n.create = AsyncMock()
            n_cls.return_value = n
            await notify_role(conn, 'super_admin', 'study.arrived', 't', 'b', '/l')
        # user 5: role default for super_admin mutes clinical -> skipped.
        # user 6: explicit disabled row -> skipped.
        n.create.assert_not_awaited()

    async def test_notify_role_sends_to_enabled_users(self):
        from api.notify import notify_role
        conn = _mock_conn()
        conn.fetchrow = AsyncMock(return_value={'id': 1})
        conn.fetch = AsyncMock(side_effect=[
            [{'id': 5}, {'id': 6}],
            [{'user_id': 6, 'event_type': 'storage.quota_breach', 'enabled': True}],
        ])
        with patch('api.notify.Notifications') as n_cls:
            n = MagicMock()
            n.create = AsyncMock()
            n_cls.return_value = n
            await notify_role(conn, 'super_admin', 'storage.quota_breach', 't', 'b', '/tenants')
        # user 5: ops event default ON for super_admin -> sent.
        # user 6: explicit enabled -> sent.
        assert n.create.await_count == 2

    async def test_notify_user_honors_role_default(self):
        from api.notify import notify_user
        conn = _mock_conn()
        conn.fetchrow = AsyncMock(return_value={'id': 42})
        conn.fetchval = AsyncMock(return_value=None)  # no explicit row
        with patch('api.notify.Notifications') as n_cls:
            n = MagicMock()
            n.create = AsyncMock()
            n_cls.return_value = n
            # super_admin + clinical event -> role default mutes it
            await notify_user(conn, '42', 'study.arrived', 't', 'b', '/l', role_slug='super_admin')
            n.create.assert_not_awaited()
            # radiologist + same event -> default ON
            await notify_user(conn, '42', 'study.arrived', 't', 'b', '/l', role_slug='radiologist')
            assert n.create.await_count == 1

    async def test_admin_scoped_roles_mute_clinical_by_default(self):
        """P2-4 (tenant_admin review): every admin-scoped role mutes clinical
        lifecycle events by default while ops alerts stay ON — not just
        super_admin."""
        from api.notify import notify_user
        for slug in ('tenant_admin', 'pacs_admin', 'emr_admin'):
            conn = _mock_conn()
            conn.fetchrow = AsyncMock(return_value={'id': 42})
            conn.fetchval = AsyncMock(return_value=None)  # no explicit row
            with patch('api.notify.Notifications') as n_cls:
                n = MagicMock()
                n.create = AsyncMock()
                n_cls.return_value = n
                await notify_user(
                    conn, '42', 'study.arrived', 't', 'b', '/l', role_slug=slug,
                )
                n.create.assert_not_awaited()
                # Operational alerts stay ON for the same role.
                await notify_user(
                    conn, '42', 'storage.quota_breach', 't', 'b', '/l', role_slug=slug,
                )
                assert n.create.await_count == 1
