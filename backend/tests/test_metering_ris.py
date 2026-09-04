"""S2-02/S2-03 (refined) — RIS metering events on the shared usage table.

API_CALLS for /ris/* are already metered by TenantMiddleware — this suite
covers only what bypasses HTTP: DICOM MWL queries (pynetdicom) and bell
notifications. Both increment per-day counters on tenant_usage_daily so the
merged platform's invoice view shows RIS activity without a parallel system.
"""

import pytest

from unittest.mock import AsyncMock, patch

from api.tokens import create_token


def _conn_ctx(conn):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _ctx():
        yield conn
    return _ctx()


class _Conn:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return []

    async def fetchval(self, sql, *args):
        return 0

    async def fetchrow(self, sql, *args):
        return None


class TestRisMeteringEvents:
    """record_mwl_query / record_notifications upsert per-day counters."""

    @pytest.mark.asyncio
    async def test_record_mwl_query_upserts(self):
        from db.metering import record_mwl_query

        conn = _Conn()
        with patch('db.metering.get_conn', return_value=conn):
            await record_mwl_query('clinic-alfa')
        assert len(conn.calls) == 1
        sql = conn.calls[0][1]
        assert 'tenant_usage_daily' in sql
        assert 'ON CONFLICT' in sql
        assert 'mwl_queries' in sql

    @pytest.mark.asyncio
    async def test_record_notifications_increments_by_count(self):
        from db.metering import record_notifications

        conn = _Conn()
        with patch('db.metering.get_conn', return_value=conn):
            await record_notifications('clinic-alfa', 3)
        sql = conn.calls[0][1]
        assert 'notifications' in sql
        # count param passed through ($2)
        assert conn.calls[0][2] == ('clinic-alfa', 3)

    @pytest.mark.asyncio
    async def test_record_never_raises_on_db_failure(self):
        from db.metering import record_mwl_query, record_notifications

        class _BoomConn:
            async def __aenter__(self):
                raise RuntimeError('pool down')

        with patch('db.metering.get_conn', return_value=_BoomConn()):
            await record_mwl_query('x')      # must not raise
            await record_notifications('x', 1)

    @pytest.mark.asyncio
    async def test_record_skips_empty_slug(self):
        from db.metering import record_mwl_query, record_notifications

        conn = _Conn()
        with patch('db.metering.get_conn', return_value=conn):
            await record_mwl_query('')
            await record_notifications(None, 1)
        assert not conn.calls, 'empty slug must not touch the DB'


class TestNotifyMetering:
    """api/notify fan-out counts created notifications once per call."""

    @pytest.mark.asyncio
    async def test_notify_role_records_count(self):
        from api.notify import notify_role

        role_row = {'id': 7}
        users = [{'id': 1}, {'id': 2}, {'id': 3}]
        pref_rows = []
        recorded = []

        conn = AsyncMock()
        conn.fetchrow.return_value = role_row
        conn.fetch.side_effect = [users, pref_rows]

        async def _fake_record(slug, count):
            recorded.append((slug, count))

        with patch('db.metering.record_notifications', new=_fake_record), \
             patch('db.conn.get_tenant_slug', return_value='default'):
            await notify_role(conn, 'radiologist', 'report.signed', 't', 'b', '/l')

        assert recorded == [('default', 3)], \
            'fan-out must record one metering event with the recipient count'

    @pytest.mark.asyncio
    async def test_notify_user_records_single(self):
        from api.notify import notify_user

        conn = AsyncMock()
        conn.fetchrow.side_effect = [{'id': 5}, {'id': 9}]
        conn.fetchval.return_value = True  # prefs enabled

        recorded = []

        async def _fake_record(slug, count):
            recorded.append((slug, count))

        with patch('db.metering.record_notifications', new=_fake_record), \
             patch('db.conn.get_tenant_slug', return_value='default'):
            await notify_user(conn, '9', 'report.ready', 't', 'b', '/l',
                              role_slug='radiologist')
        assert recorded == [('default', 1)]

    @pytest.mark.asyncio
    async def test_notify_metering_never_blocks_delivery(self):
        """A metering failure must not fail the notification fan-out."""
        from api.notify import notify_role

        conn = AsyncMock()
        conn.fetchrow.return_value = {'id': 7}
        conn.fetch.side_effect = [[{'id': 1}], []]

        async def _boom(slug, count):
            raise RuntimeError('metering down')

        with patch('db.metering.record_notifications', new=_boom), \
             patch('db.conn.get_tenant_slug', return_value='default'):
            await notify_role(conn, 'radiologist', 'report.signed', 't', 'b', '/l')
        # no exception == notifications still delivered


class TestMwlFindMetering:
    """handle_find_async records an MWL_QUERIES event per C-FIND."""

    @pytest.mark.asyncio
    async def test_cfind_records_mwl_query(self):
        from contextlib import asynccontextmanager
        from unittest.mock import patch
        from pydicom.dataset import Dataset

        recorded = []

        async def _fake_record(slug):
            recorded.append(slug)

        class _FakeConn:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                return False

        async def fake_search(self, **kwargs):
            return [], 0

        @asynccontextmanager
        async def _scope():
            yield

        from dcm.server import handle_find_async
        query_ds = Dataset()
        with patch('dcm.server._tenant_scope_for_ae',
                   AsyncMock(return_value=('default', {}))), \
             patch('dcm.server.tenant_db_scope', lambda s, i: _scope()), \
             patch('db.conn.get_conn', return_value=_FakeConn()), \
             patch('db.worklist.Worklist.search', fake_search), \
             patch('db.metering.record_mwl_query', new=_fake_record):
            await handle_find_async(query_ds, ae_title='PERF')

        assert recorded == ['default'], \
            'every MWL C-FIND must record an mwl_queries event'


class TestUsageBreakdownApi:
    """S2-03: usage endpoints expose the RIS activity columns."""

    @pytest.mark.asyncio
    async def test_platform_usage_sums_ris_columns(self):
        from db.metering import get_platform_usage

        conn = AsyncMock()
        conn.fetch.return_value = []
        with patch('db.metering.get_conn', return_value=_conn_ctx(conn)):
            await get_platform_usage(days=30)
        sql = conn.fetch.call_args[0][0]
        assert 'SUM(u.mwl_queries)' in sql
        assert 'SUM(u.notifications)' in sql

    def test_tenant_usage_totals_include_ris(self):
        from unittest.mock import patch as _patch

        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from api.auth import TokenAuth
        from api.metering import MeteringUsageHandler

        app = Starlette(
            routes=[Route('/api/tenants/{id}/usage', MeteringUsageHandler)],
            middleware=[Middleware(AuthenticationMiddleware, backend=TokenAuth(),
                                   on_error=TokenAuth.on_auth_error)],
        )
        daily = [
            {'slug': 'acme-clinic', 'day': '2026-08-20', 'api_calls': 10,
             'storage_bytes': 100, 'active_users': 2, 'mwl_queries': 4,
             'notifications': 6},
            {'slug': 'acme-clinic', 'day': '2026-08-21', 'api_calls': 5,
             'storage_bytes': 100, 'active_users': 1, 'mwl_queries': 1,
             'notifications': 2},
        ]

        def _build_conn():
            conn = AsyncMock()
            conn.fetchrow.return_value = {
                'id': 1, 'name': 'Acme Clinic', 'slug': 'acme-clinic'}
            return conn

        # TokenAuth's own active-user probe (separate pool import).
        auth_conn = AsyncMock()
        auth_conn.fetchrow.return_value = {'status': 'active', 'token_version': 0}

        user = {'id': 1, 'admin': True}
        with _patch('api.tokens.config',
                    {'secret': 'test-secret-key-32-bytes-long!!!'}):
            token = create_token(user, permissions=['*'])
            headers = {'X-Auth-Pacs': token, 'Authorization': f'Bearer {token}'}

            with _patch('api.auth.get_conn', return_value=_conn_ctx(auth_conn)), \
                 _patch('api.metering.get_conn',
                        return_value=_conn_ctx(_build_conn())), \
                 _patch('api.metering.get_usage', AsyncMock(return_value=daily)):
                with TestClient(app) as client:
                    resp = client.get('/api/tenants/1/usage', headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['totals']['mwl_queries'] == 5
        assert body['totals']['notifications'] == 8
        assert body['usage_daily'][0]['mwl_queries'] == 4
