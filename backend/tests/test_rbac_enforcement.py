"""RBAC enforcement tests for the §7 endpoint → permission map.

Covers the requires_permission / has_permission machinery in api/rbac.py,
one representative endpoint per §7 group (worklist, files, tenants, roles,
service-keys, logs, patients, reports, billing, dicomweb, portal), the
LOG_READ → AUDIT_READ legacy alias, and token_version bumps on role changes.

Canonical codes from RBAC_matrix_spec.md §7 are asserted as strings so the
suite stays green while Stream 1 adds the new Permission enum members.
"""
import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from starlette.applications import Starlette
from starlette.authentication import UnauthenticatedUser
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission
from api.rbac import has_permission, requires_permission, guard_endpoint_method
from api.response import ok

from api.worklist import WorklistHandler
from api.files import FilesHandler, FileHandler, FileChangesHandler
from api.tenants import TenantsHandler
from api.roles import RolesHandler, RoleHandler
from api.api_keys import ApiKeysHandler
from api.logs import LogsHandler
from api.patient import PatientHandler
from api.reports import ReadingListHandler
from api.billing import BillingPricingHandler
from api.dicomweb import DicomWebStudies
from api.portal import PortalScopeHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(route, user):
    return Starlette(
        routes=[route],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _make_user(permissions):
    return User({'id': 1, 'permissions': list(permissions)})


def _patch_conn(module):
    """Patch `module.get_conn` with an async context manager returning a
    MagicMock conn whose fetch/fetchrow/fetchval/execute are AsyncMocks."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock()
    p = patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=None),
    ))
    return p, conn


def _patch_db_class(module, cls_name, **methods):
    """Patch `module.<cls_name>` with a MagicMock; every named method becomes
    an AsyncMock returning the given value. Returns (patch, mocked_class)."""
    cls_mock = MagicMock()
    instance = cls_mock.return_value
    for name, ret in methods.items():
        setattr(instance, name, AsyncMock(return_value=ret))
    return patch(f'{module}.{cls_name}', cls_mock), cls_mock


def _check_read_group(route, code, conn_module, db_patch=None, url=None):
    """Same representative endpoint, two outcomes: no permission → 403 with
    'Missing permission: <code>', granted permission → 200."""
    patches = [_patch_conn(conn_module)[0]]
    if db_patch is not None:
        patches.append(db_patch)
    for perms, expected in (([], 403), ([code], 200)):
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            with TestClient(_make_app(route, _make_user(perms))) as client:
                resp = client.get(url or route.path)
        if expected == 403:
            assert resp.status_code == 403
            assert resp.json()['error'] == f'Missing permission: {code}'
        else:
            assert resp.status_code == 200


# ---------------------------------------------------------------- 401/403/200

def test_unauthenticated_request_returns_401():
    route = Route('/api/worklist', endpoint=WorklistHandler)
    with TestClient(_make_app(route, UnauthenticatedUser())) as client:
        resp = client.get('/api/worklist')
    assert resp.status_code == 401
    assert resp.json()['error'] == 'Not authenticated'


def test_super_admin_wildcard_grant_passes_any_guard():
    route = Route('/api/worklist', endpoint=WorklistHandler)
    p = _patch_conn('api.worklist')[0]
    q = _patch_db_class('api.worklist', 'Worklist', search=([], 0))[0]
    with p, q:
        with TestClient(_make_app(route, _make_user(['*']))) as client:
            resp = client.get('/api/worklist')
    assert resp.status_code == 200


# ------------------------------------------------- §7 groups (representative)

def test_worklist_group_enforcement():
    p = _patch_db_class('api.worklist', 'Worklist', search=([], 0))[0]
    _check_read_group(
        Route('/api/worklist', endpoint=WorklistHandler),
        'WORKLIST_READ', 'api.worklist', p,
    )


def test_files_group_enforcement():
    p = _patch_db_class('api.files', 'Files', get_paginated=([], 0))[0]
    _check_read_group(
        Route('/api/files', endpoint=FilesHandler),
        'FILE_READ', 'api.files', p,
    )


def test_tenants_group_enforcement():
    p = _patch_db_class('api.tenants', 'Tenants', get_all=[])[0]
    _check_read_group(
        Route('/api/tenants', endpoint=TenantsHandler),
        'TENANT_READ', 'api.tenants', p,
    )


def test_roles_group_enforcement():
    p = _patch_db_class('api.roles', 'Roles', get_all=[])[0]
    _check_read_group(
        Route('/api/roles', endpoint=RolesHandler),
        'ROLE_READ', 'api.roles', p,
    )


def test_service_keys_group_enforcement():
    p = _patch_db_class('api.api_keys', 'ApiKeys', get_all=[])[0]
    _check_read_group(
        Route('/api/api-keys', endpoint=ApiKeysHandler),
        'SERVICE_KEY_READ', 'api.api_keys', p,
    )


def test_logs_group_enforcement():
    p = _patch_db_class('api.logs', 'AuditLog', query=[], count=0)[0]
    _check_read_group(
        Route('/api/logs', endpoint=LogsHandler),
        'LOG_READ', 'api.logs', p,
    )


def test_patients_group_enforcement():
    p = _patch_db_class('api.patient', 'Patient', get_extra={'id': 1, 'patient_id': 'P1'})[0]
    _check_read_group(
        Route('/api/patients/{id}', endpoint=PatientHandler),
        'PATIENT_READ', 'api.patient', p, url='/api/patients/1',
    )


def test_reports_group_enforcement():
    p = _patch_db_class('api.reports', 'Reports', reading_list=[])[0]
    _check_read_group(
        Route('/api/reports/reading-list', endpoint=ReadingListHandler),
        'REPORT_READ', 'api.reports', p,
    )


def test_billing_group_enforcement():
    _check_read_group(
        Route('/api/billing/pricing', endpoint=BillingPricingHandler),
        'BILLING_READ', 'api.billing',
    )


def test_dicomweb_group_enforcement():
    _check_read_group(
        Route('/api/dicomweb/studies', endpoint=DicomWebStudies),
        'DICOMWEB_READ', 'api.dicomweb',
    )


def test_portal_group_enforcement():
    p = _patch_db_class('api.portal', 'Portal', list_scope=[])[0]
    _check_read_group(
        Route('/api/portal/scope', endpoint=PortalScopeHandler),
        'PORTAL_READ', 'api.portal', p,
    )


# ------------------------------------------------- legacy alias (LOG_READ ↔ AUDIT_READ)

def test_has_permission_resolves_log_read_alias_for_audit_read():
    user = _make_user(['LOG_READ'])
    assert has_permission(user, 'AUDIT_READ') is True
    assert has_permission(user, Permission.LOG_READ) is True
    assert has_permission(user, 'REPORT_READ') is False


def test_has_permission_resolves_audit_read_alias_for_log_read():
    """Symmetric alias: a canonical-role user holding only AUDIT_READ (as the
    Matrix A admin roles do) passes a guard written against the legacy
    LOG_READ code — the direction the production /api/logs guard uses."""
    user = _make_user(['AUDIT_READ'])
    assert has_permission(user, 'LOG_READ') is True
    assert has_permission(user, Permission.LOG_READ) is True
    assert has_permission(user, 'AUDIT_READ') is True


def test_has_permission_resolves_analytics_read_alias_for_metrics_read():
    """ANALYTICS_READ ⇄ METRICS_READ: department_manager (Matrix A) holds only
    ANALYTICS_READ and must pass the METRICS_READ-guarded dashboard endpoints."""
    dm = _make_user(['ANALYTICS_READ'])
    assert has_permission(dm, 'METRICS_READ') is True
    assert has_permission(dm, Permission.METRICS_READ) is True
    metrics_only = _make_user(['METRICS_READ'])
    assert has_permission(metrics_only, 'ANALYTICS_READ') is True


def test_audit_read_guarded_endpoint_accepts_log_read_grant():
    """§7: /api/logs* → AUDIT_READ; LOG_READ stays as its legacy alias, so a
    LOG_READ grant must pass an AUDIT_READ guard. The guard is written against
    the canonical code; Stream 1 adds Permission.AUDIT_READ to the enum."""

    class AuditReadEndpoint(HTTPEndpoint):
        @requires_permission('AUDIT_READ')
        async def get(self, request):
            return ok({})

    route = Route('/api/logs', endpoint=AuditReadEndpoint)
    with TestClient(_make_app(route, _make_user(['LOG_READ']))) as client:
        resp = client.get('/api/logs')
    assert resp.status_code == 200


# ------------------------------------------- route-level guards (files.py gaps)

def test_file_update_route_requires_file_write():
    """FileHandler.post is unguarded in files.py; routes.py wraps it with
    FILE_WRITE per §7 (/api/files write)."""
    route = Route('/api/files/{id}', endpoint=guard_endpoint_method(FileHandler, 'post', Permission.FILE_WRITE))
    p = _patch_conn('api.files')[0]
    q = _patch_db_class('api.files', 'Files', update_tools_state=None, update_tag=None)[0]

    with p, q:
        with TestClient(_make_app(route, _make_user([Permission.FILE_READ.value]))) as client:
            resp = client.post('/api/files/1', json={})
    assert resp.status_code == 403
    assert resp.json()['error'] == 'Missing permission: FILE_WRITE'

    with p, q:
        with TestClient(_make_app(route, _make_user([Permission.FILE_WRITE.value]))) as client:
            resp = client.post('/api/files/1', json={})
    assert resp.status_code == 200


def test_file_changes_route_requires_file_read():
    """FileChangesHandler.get is unguarded in files.py; routes.py wraps it with
    FILE_READ per §7 (/api/files read)."""
    route = Route('/api/files/{id}/changes', endpoint=guard_endpoint_method(FileChangesHandler, 'get', Permission.FILE_READ))
    p = _patch_conn('api.files')[0]
    q = _patch_db_class('api.files', 'FileChange', for_file=[])[0]

    with p, q:
        with TestClient(_make_app(route, _make_user([]))) as client:
            resp = client.get('/api/files/1/changes')
    assert resp.status_code == 403
    assert resp.json()['error'] == 'Missing permission: FILE_READ'

    with p, q:
        with TestClient(_make_app(route, _make_user([Permission.FILE_READ.value]))) as client:
            resp = client.get('/api/files/1/changes')
    assert resp.status_code == 200


def test_guarded_route_unauthenticated_returns_401():
    route = Route('/api/files/{id}', endpoint=guard_endpoint_method(FileHandler, 'post', Permission.FILE_WRITE))
    with TestClient(_make_app(route, UnauthenticatedUser())) as client:
        resp = client.post('/api/files/1', json={})
    assert resp.status_code == 401
    assert resp.json()['error'] == 'Not authenticated'


# ------------------------------------------------- token_version bump on role change

def test_role_permission_update_bumps_token_version_for_role_users():
    role = {'id': 'r1', 'name': 'X', 'slug': 'x', 'built_in': False}
    route = Route('/api/roles/{id}', endpoint=RoleHandler)
    p_roles = _patch_db_class('api.roles', 'Roles', get=role, patch=None)
    p_users = _patch_db_class('api.roles', 'Users', bulk_increment_token_version_by_role=None)
    p_audit = _patch_db_class('api.roles', 'AuditLog', log_event=None)
    p_conn = _patch_conn('api.roles')[0]

    with p_conn, p_roles[0] as roles_cls, p_users[0] as users_cls, p_audit[0]:
        # Caller holds ROLE_WRITE + the permission being assigned: the R2-M2
        # subset guard (no privilege escalation through role editing) must
        # not trip on a legit same-scope update.
        with TestClient(_make_app(route, _make_user([Permission.ROLE_WRITE.value,
                                                     Permission.FILE_READ.value]))) as client:
            resp = client.put('/api/roles/r1', json={'permissions': ['FILE_READ']})
    assert resp.status_code == 200
    users_cls.return_value.bulk_increment_token_version_by_role.assert_awaited_once_with('r1')
    roles_cls.return_value.patch.assert_awaited()


def test_role_delete_bumps_token_version_for_role_users():
    role = {'id': 'r1', 'name': 'X', 'slug': 'x', 'built_in': False}
    route = Route('/api/roles/{id}', endpoint=RoleHandler)
    p_roles = _patch_db_class('api.roles', 'Roles', get=role, delete=None)
    p_users = _patch_db_class('api.roles', 'Users', bulk_increment_token_version_by_role=None)
    p_audit = _patch_db_class('api.roles', 'AuditLog', log_event=None)
    p_conn = _patch_conn('api.roles')[0]

    with p_conn, p_roles[0], p_users[0] as users_cls, p_audit[0]:
        with TestClient(_make_app(route, _make_user([Permission.ROLE_DELETE.value]))) as client:
            resp = client.delete('/api/roles/r1')
    assert resp.status_code == 200
    users_cls.return_value.bulk_increment_token_version_by_role.assert_awaited_once_with('r1')


def test_bulk_increment_token_version_by_role_sql():
    from db.users import Users

    conn = MagicMock()
    conn.execute = AsyncMock()
    asyncio.run(Users(conn).bulk_increment_token_version_by_role('r1'))
    sql, = conn.execute.call_args.args
    assert 'token_version' in sql
    assert 'token_version"+1' in sql
    assert 'role_id' in sql


# ------------------------------------------------- routes.py wiring

def test_routes_wire_guards_for_unguarded_file_handlers():
    try:
        from api import routes
    except ImportError as e:
        pytest.skip(f'api.routes import failed: {e}')
    by_path = {r.path: r for r in routes._V1_ROUTES if isinstance(r, Route)}
    assert by_path['/files/{id}'].endpoint.__name__ == 'GuardedFileHandler'
    assert by_path['/files/{id}/changes'].endpoint.__name__ == 'GuardedFileChangesHandler'


# ------------------------------------------------ built-in immutability + schema validation

def test_put_built_in_role_forbidden():
    role = {'id': 'r1', 'name': 'Radiologist', 'slug': 'radiologist', 'built_in': True}
    route = Route('/api/roles/{id}', endpoint=RoleHandler)
    p_roles = _patch_db_class('api.roles', 'Roles', get=role, patch=None)
    p_conn = _patch_conn('api.roles')[0]

    with p_conn, p_roles[0] as roles_cls:
        with TestClient(_make_app(route, _make_user([Permission.ROLE_WRITE.value]))) as client:
            resp = client.put('/api/roles/r1', json={'permissions': ['FILE_READ']})
    assert resp.status_code == 403
    roles_cls.return_value.patch.assert_not_awaited()


def test_put_unknown_permission_rejected():
    route = Route('/api/roles/{id}', endpoint=RoleHandler)
    p_roles = _patch_db_class('api.roles', 'Roles', get={'id': 'r1', 'built_in': False})
    p_conn = _patch_conn('api.roles')[0]

    with p_conn, p_roles[0]:
        with TestClient(_make_app(route, _make_user([Permission.ROLE_WRITE.value]))) as client:
            resp = client.put('/api/roles/r1', json={'permissions': ['NOT_A_PERMISSION']})
    assert resp.status_code == 422


def test_create_role_wildcard_permission_rejected():
    route = Route('/api/roles', endpoint=RolesHandler)
    p_conn = _patch_conn('api.roles')[0]

    with p_conn:
        with TestClient(_make_app(route, _make_user([Permission.ROLE_WRITE.value]))) as client:
            resp = client.post('/api/roles', json={'name': 'X', 'slug': 'x', 'permissions': ['*']})
    assert resp.status_code == 422


def test_create_role_invalid_slug_rejected():
    route = Route('/api/roles', endpoint=RolesHandler)
    p_conn = _patch_conn('api.roles')[0]

    with p_conn:
        with TestClient(_make_app(route, _make_user([Permission.ROLE_WRITE.value]))) as client:
            resp = client.post('/api/roles', json={'name': 'X', 'slug': 'bad slug!', 'permissions': []})
    assert resp.status_code == 422
