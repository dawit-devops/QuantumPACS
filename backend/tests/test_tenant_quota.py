"""AD2 (§2.10 ADM-17): audited storage-quota overrides + list enrichment.

A quota change on PUT /tenants/{id} must carry a justification and emit
`tenant.quota_changed` with old/new/justification; non-quota updates stay
justification-free. The tenants list must surface storage_used_bytes /
storage_pct so the UI can render the 80/90/100 alerts.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tenants import TenantHandler, TenantsHandler
from api.validate import validation_exception_handler, _ValidationException

TENANT = {
    'id': 't-1', 'slug': 'hospital-a', 'name': 'Hospital A',
    'status': 'active', 'storage_quota_bytes': 10 * 1024**3,
}


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse

    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


# Platform admin: the '*' wildcard is what a real super_admin JWT carries —
# has_permission honors it only for admin-flagged users.
ADMIN = lambda: User({'id': 1, 'admin': True, 'permissions': ['*']})  # noqa: E731


def _patch_deps(existing=TENANT):
    mock_conn = MagicMock()
    mock_tenants = MagicMock()
    mock_tenants.get = AsyncMock(return_value=existing)
    mock_tenants.patch = AsyncMock()
    mock_audit = MagicMock()
    mock_audit.log_event = AsyncMock()
    patches = (
        patch('api.tenants.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None),
        )),
        patch('api.tenants.Tenants', return_value=mock_tenants),
        patch('api.tenants.AuditLog', return_value=mock_audit),
    )
    # Pool close must be a no-op in tests; patch it defensively.
    patches += (patch('api.tenants.TenantConnectionPool.close', new=AsyncMock()),)
    return patches, mock_tenants, mock_audit


class TestQuotaOverrideJustification:
    def _app(self):
        return _make_app(
            [Route('/tenants/{id}', endpoint=TenantHandler)], ADMIN(),
        )

    def test_quota_change_without_justice_returns_400(self):
        patches, tenants, audit = _patch_deps()
        with patches[0], patches[1], patches[2], patches[3]:
            client = TestClient(self._app())
            resp = client.put(
                '/tenants/t-1',
                json={'storage_quota_bytes': 20 * 1024**3},
            )
        assert resp.status_code == 400
        tenants.patch.assert_not_awaited()

    def test_blank_justification_is_rejected_like_missing(self):
        patches, tenants, _ = _patch_deps()
        with patches[0], patches[1], patches[2], patches[3]:
            client = TestClient(self._app())
            resp = client.put(
                '/tenants/t-1',
                json={
                    'storage_quota_bytes': 20 * 1024**3,
                    'quota_justification': '   ',
                },
            )
        assert resp.status_code == 400
        tenants.patch.assert_not_awaited()

    def test_quota_change_with_justification_audited(self):
        patches, tenants, audit = _patch_deps()
        with patches[0], patches[1], patches[2], patches[3]:
            client = TestClient(self._app())
            resp = client.put(
                '/tenants/t-1',
                json={
                    'storage_quota_bytes': 20 * 1024**3,
                    'quota_justification': 'Growth plan upgrade approved by IT',
                },
            )
        assert resp.status_code == 200
        event = audit.log_event.await_args.kwargs['event_type']
        assert event == 'tenant.quota_changed'
        details = audit.log_event.await_args.kwargs['details']
        assert details['old_bytes'] == TENANT['storage_quota_bytes']
        assert details['new_bytes'] == 20 * 1024**3
        assert 'approved by IT' in details['justification']

    def test_rename_does_not_require_justification(self):
        patches, _, audit = _patch_deps()
        with patches[0], patches[1], patches[2], patches[3]:
            client = TestClient(self._app())
            resp = client.put('/tenants/t-1', json={'name': 'Hospital A West'})
        assert resp.status_code == 200
        audit.log_event.assert_not_awaited()


class TestTenantsListQuotaFields:
    def test_list_carries_storage_used_and_pct(self):
        """The card quota bar needs utilization from get_stats — without it
        every tenant renders 0 B used and the 80/90/100 alerts never fire."""
        stats = {
            'user_count': 5, 'study_count': 7, 'file_count': 9,
            'last_activity': None,
            'storage_used_bytes': 9 * 1024**3,
            'storage_pct': 90.0,
        }
        pool_info = {'db_name': 'hospital_a'}
        mock_conn = MagicMock()
        with (
            patch('api.tenants.get_conn', return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=None),
            )),
            patch('api.tenants.Tenants') as tenants_cls,
            patch('api.tenants._pool_info_for', return_value=pool_info),
        ):
            instance = tenants_cls.return_value
            instance.get_all = AsyncMock(return_value=[dict(TENANT)])
            instance.get_stats = AsyncMock(return_value=dict(stats))
            client = TestClient(_make_app(
                [Route('/tenants', endpoint=TenantsHandler)], ADMIN(),
            ))
            resp = client.get('/tenants')
        assert resp.status_code == 200
        row = resp.json()['data'][0]
        assert row['storage_used_bytes'] == 9 * 1024**3
        assert row['storage_pct'] == 90.0
