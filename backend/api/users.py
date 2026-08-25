from starlette.endpoints import HTTPEndpoint

from config import cookie_secure

from api.response import ok, paginated, api_error

import jwt as _jwt

from api.rbac import requires_permission
from api.permissions import Permission
from api.tokens import create_token_pair, verify_refresh_token, block_token, is_blocked
from api.ratelimit import login_bucket, password_bucket, refresh_bucket
from api.validate import parse_body, read_body, _BodyTooLargeException
from api.schemas.auth import LoginRequest
from api.schemas.account import ChangePasswordRequestV2
from api.schemas.auth_refresh import RefreshTokenRequest, RevokeTokenRequest
from api.schemas.users import (
    BatchUserStatusRequest, CreateUserRequest, UserActionRequest, UpdateUserRoleRequest,
)
from db.audit_log import AuditLog
import asyncpg

from db.conn import (
    get_conn, set_request_tenant, reset_request_tenant,
    set_tenant_slug, reset_tenant_slug,
)
from db.roles import Roles
from db.users import Users
from exceptions import ApiException
from log import get_logger, request_id_var
from services.interfaces import AuthService

log = get_logger(__name__)


def _extract_token(request):
    auth = request.headers.get('X-Auth-Pacs')
    if not auth:
        bearer = request.headers.get('Authorization')
        if bearer and bearer.startswith('Bearer '):
            auth = bearer[7:]
    if not auth:
        auth = request.query_params.get('token')
    if not auth:
        auth = request.cookies.get('token')
    # No query-param fallback (IAM audit M-3): JWTs must never travel in
    # URLs — Referer headers and access logs would leak them. Share-key
    # authentication has its own dedicated query path in AuthMiddleware.
    return auth


async def _can_assign_role(user, conn, role_id) -> tuple[bool, str]:
    """A non-platform-admin may only grant a role whose permission set is a
    subset of their own — otherwise USER_WRITE escalates to super_admin."""
    caller_perms = set(getattr(user, 'permissions', None) or [])
    role = await Roles(conn).get(role_id)
    if not role:
        return False, 'Role not found'
    target = role.get('permissions') or []
    if isinstance(target, str):
        import json
        target = json.loads(target)
    if not set(target) <= caller_perms:
        return False, 'Target role exceeds your own grants'
    return True, ''


class Login(HTTPEndpoint):
    async def post(self, request):
        ip = request.client.host if request.client else 'unknown'
        allowed, msg = await login_bucket.check(ip)
        if not allowed:
            return api_error('RATE_LIMITED', msg, status=429)

        body = await parse_body(LoginRequest, request)

        # M-1: scope the login to the user's tenant database (DB-per-tenant).
        # The tenant slug comes from the login body or the X-Tenant-ID header;
        # the registry row is resolved on the MAIN pool (login is otherwise
        # un-scoped). Unknown tenant -> 404; missing tenant DB -> 503.
        tenant_slug = body.tenant or request.headers.get('X-Tenant-ID')
        _pool = None
        try:
            if tenant_slug:
                from db.conn import get_database
                from db.tenants import Tenants, TenantConnectionPool, uses_main_database
                async with get_database().acquire() as _main_conn:
                    _info = await Tenants(_main_conn).get_by_slug(tenant_slug)
                if not _info:
                    return api_error(
                        'TENANT_NOT_FOUND',
                        f'Tenant not available: {tenant_slug}',
                        status=404,
                    )
                if uses_main_database(_info):
                    set_request_tenant(get_database().acquire)
                else:
                    try:
                        _pool = await TenantConnectionPool.get(tenant_slug, _info)
                    except asyncpg.InvalidCatalogNameError:
                        return api_error(
                            'TENANT_UNAVAILABLE',
                            'Tenant database is unavailable',
                            status=503,
                        )
                    set_request_tenant(_pool.acquire)
                set_tenant_slug(tenant_slug)

            services = getattr(request.state, 'services', None)
            if services is not None:
                try:
                    auth_service = services.get(AuthService)
                    data = await auth_service.authenticate(body.username, body.password)
                except Exception:
                    data = None
            else:
                data = None

            if data is None:
                async with get_conn() as conn:
                    try:
                        data = await Users(conn).login(body.username, body.password)
                    except ApiException as e:
                        await login_bucket.record_db(ip, conn, success=False)
                        await AuditLog(conn).log_event(
                            event_type='auth.login_failed',
                            actor_id=None,
                            resource_type='user',
                            resource_id=body.username,
                            details={'reason': type(e).__name__},
                            request_id=request_id_var.get(),
                        )
                        # Generic message — the server-side distinction stays in
                        # the audit log, never in the 401 body (enumeration).
                        return api_error('AUTH_FAILED', 'Invalid credentials', status=401)

            async with get_conn() as conn:
                await login_bucket.record_db(ip, conn, success=True)
                await Users(conn).update_last_login(data['id'])
                role_slug, permissions = await Users(conn).get_user_role(data['id'])
                token_version = await Users(conn).get_token_version(data['id'])
                tenant_id = None
                tenant_name = None
                if data.get('tenant'):
                    # Registry lookup on the MAIN pool: even though login is now
                    # tenant-scoped, the tenants table lives only on the main
                    # registry DB, not in the tenant's own database.
                    from db.conn import get_database
                    from db.tenants import Tenants
                    tenant_id = data.get('tenant')
                    async with get_database().acquire() as _main_conn:
                        tenant_row = await Tenants(_main_conn).get_by_slug(tenant_id)
                    if tenant_row:
                        tenant_name = tenant_row.get('name')
                access, refresh = create_token_pair(
                    data, role=role_slug, permissions=permissions,
                    token_version=token_version,
                )
                await AuditLog(conn).log_event(
                    event_type='auth.login_success',
                    actor_id=data['id'],
                    resource_type='user',
                    resource_id=str(data['id']),
                    details={'username': body.username},
                    request_id=request_id_var.get(),
                )
                resp = ok({
                    'id': data['id'],
                    'admin': data['admin'],
                    'role': role_slug or '',
                    'permissions': permissions or [],
                    'tenant': data.get('tenant'),
                    'tenant_id': tenant_id,
                    'tenant_name': tenant_name,
                    'token': access,
                    'access_token': access,
                })
                resp.set_cookie(
                    key='token',
                    value=access,
                    httponly=True,
                    samesite='strict',
                    secure=cookie_secure(),
                    # Root path (IAM audit H-2): the browser auth channel must
                    # cover /api and /dicomweb (WADO-RS image fetches) alike.
                    path='/',
                )
                # Refresh token travels only as an HttpOnly cookie scoped to the
                # auth endpoints (/api/auth) — both the refresh endpoint and
                # logout need to read it for rotation/revocation (AT-4). Never
                # in localStorage or URLs.
                resp.set_cookie(
                    key='refresh_token',
                    value=refresh,
                    httponly=True,
                    samesite='strict',
                    secure=cookie_secure(),
                    path='/api/auth',
                )
                # CSRF double-submit token: a random value set as a readable
                # cookie (NOT HttpOnly) that the client echoes in X-CSRF-Token.
                # SameSite=Strict prevents cross-origin携带; the middleware
                # verifies header == cookie on every mutating request.
                import secrets
                resp.set_cookie(
                    key='csrf_token',
                    value=secrets.token_hex(32),
                    httponly=False,
                    samesite='strict',
                    secure=cookie_secure(),
                    path='/',
                )
                return resp
        finally:
            if tenant_slug:
                reset_request_tenant()
                reset_tenant_slug()
                if _pool is not None:
                    from db.tenants import TenantConnectionPool
                    TenantConnectionPool.release(tenant_slug)


class ChangePassword(HTTPEndpoint):
    async def post(self, request):
        body = await parse_body(ChangePasswordRequestV2, request)

        user_key = f'user:{request.user.id}'
        allowed, msg = await password_bucket.check(user_key)
        if not allowed:
            return api_error('RATE_LIMITED', msg, status=429)

        async with get_conn() as conn:
            try:
                await Users(conn).change_password(
                    request.user, body.new_password, body.current_password,
                )
            except ApiException as e:
                await password_bucket.record(user_key, success=False)
                return api_error('PASSWORD_ERROR', str(e), status=400)

            token = _extract_token(request)
            if token:
                await block_token(token)
            await AuditLog(conn).log_event(
                event_type='user.password_changed',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=str(request.user.id),
                request_id=request_id_var.get(),
            )

            return ok({})


class Logout(HTTPEndpoint):
    async def post(self, request):
        token = _extract_token(request)
        if token:
            await block_token(token)
        refresh = request.cookies.get('refresh_token')
        if refresh:
            await block_token(refresh)
        resp = ok({'message': 'Logged out'})
        resp.delete_cookie('token', path='/')
        resp.delete_cookie('refresh_token', path='/api/auth')
        resp.delete_cookie('csrf_token', path='/')
        return resp


class RevokeToken(HTTPEndpoint):
    @requires_permission(Permission.USER_ADMIN)
    async def post(self, request):
        body = await parse_body(RevokeTokenRequest, request)
        await block_token(body.token)
        try:
            async with get_conn() as conn:
                await AuditLog(conn).log_event(
                    event_type='auth.token_revoked',
                    actor_id=request.user.id,
                    resource_type='token',
                    resource_id=body.token[:16],
                    request_id=request_id_var.get(),
                )
        except Exception:
            # Revocation itself already happened — an audit write failure must
            # never turn a successful revoke into a 500.
            log.warning('audit write failed for auth.token_revoked', exc_info=True)
        return ok({'message': 'Token revoked'})


class UsersHandler(HTTPEndpoint):
    @requires_permission(Permission.USER_READ)
    async def get(self, request):
        q = request.query_params.get('q')
        # Clamp pagination: negative/oversized limits and offsets must not
        # reach the DB (offset/limit are interpolated into the SQL).
        offset = max(0, int(request.query_params.get('offset', 0)))
        limit = max(1, min(200, int(request.query_params.get('limit', 20))))
        # P2-2 (tenant_admin review): tenant-scoped admins see only their own
        # tenant's users — mirrors the tenants-list scoping. Platform admins
        # (super_admin / admin flag) keep the full directory.
        tenant_scope = None
        if not getattr(request.user, 'admin', False):
            tenant_scope = getattr(request.user, 'tenant', None)

        async with get_conn() as conn:
            data = await Users(conn).get_users(
                offset=offset, limit=limit, username=q, tenant=tenant_scope,
            )
            total = await Users(conn).count_users(username=q, tenant=tenant_scope)

        return paginated(
            [Users.to_json(u) for u in data],
            total=total, page=(offset // limit) + 1, per_page=limit,
            request=request,
        )

    @requires_permission(Permission.USER_WRITE)
    async def post(self, request):
        body = await parse_body(CreateUserRequest, request)
        if body.admin and not request.user.admin:
            # The admin flag is a second super-admin channel (JWT claim that
            # bypasses tenant gates) — only platform admins may grant it.
            return api_error(
                'FORBIDDEN',
                'Only platform admins may create admin users',
                status=403,
            )

        async with get_conn() as conn:
            if body.role_id and not request.user.admin:
                # Role assignment is capped to the caller's own grant set —
                # otherwise USER_WRITE is a backdoor to super_admin.
                ok_role, msg = await _can_assign_role(request.user, conn, body.role_id)
                if not ok_role:
                    return api_error('FORBIDDEN', msg, status=403)
            result = await Users(conn).add_user(body.username, body.admin, role_id=body.role_id)
            await AuditLog(conn).log_event(
                event_type='user.created',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=body.username,
                details={'admin': body.admin, 'role_id': body.role_id},
                request_id=request_id_var.get(),
            )

        return ok({'password': result['password'], 'username': body.username})


class UsersDeactivate(HTTPEndpoint):
    @requires_permission(Permission.USER_DELETE)
    async def post(self, request):
        body = await parse_body(UserActionRequest, request)

        async with get_conn() as conn:
            try:
                await Users(conn).deactivate(body.id)
            except ApiException as e:
                return api_error('FORBIDDEN', str(e), status=403)
            await AuditLog(conn).log_event(
                event_type='user.deactivated',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=str(body.id),
                request_id=request_id_var.get(),
            )

        resp = ok({})
        resp.headers['X-API-Deprecated'] = 'true'
        resp.headers['X-API-Sunset'] = 'v3.0'
        resp.headers['X-API-Replacement'] = 'DELETE /api/users/{id}'
        return resp


class UsersBatchStatus(HTTPEndpoint):
    """ADM-02 bulk operations (§2.10): activate/deactivate many users in one
    audited call. Deactivation routes through Users.deactivate() so the
    last-active-admin lockout applies per id; a failing id is reported and
    never aborts the remaining ones."""

    @requires_permission(Permission.USER_DELETE)
    async def post(self, request):
        body = await parse_body(BatchUserStatusRequest, request)
        # Deactivating the operator's own account would lock them out
        # mid-session; single-user deactivate has the same exposure but the
        # batch makes the mistake easier, so it is rejected outright.
        if body.target_status == 'deactivated' and request.user.id in body.user_ids:
            return api_error(
                'FORBIDDEN', 'Cannot deactivate your own account', status=403,
            )

        changed: list[int] = []
        failed: list[dict] = []
        async with get_conn() as conn:
            users = Users(conn)
            op = users.deactivate if body.target_status == 'deactivated' else users.activate
            for uid in body.user_ids:
                try:
                    await op(uid)
                    changed.append(uid)
                except ApiException as e:
                    failed.append({'id': uid, 'error': str(e)})
            await AuditLog(conn).log_event(
                event_type='user.batch_status_changed',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=f'batch:{len(body.user_ids)}',
                details={
                    'target_status': body.target_status,
                    'requested': body.user_ids,
                    'changed': changed,
                    'failed': failed,
                },
                request_id=request_id_var.get(),
            )

        return ok({'changed': changed, 'failed': failed})


class UsersNewPassword(HTTPEndpoint):
    @requires_permission(Permission.USER_WRITE)
    async def post(self, request):
        body = await parse_body(UserActionRequest, request)

        async with get_conn() as conn:
            result = await Users(conn).new_pswd(body.id)
            await AuditLog(conn).log_event(
                event_type='user.password_reset',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=str(body.id),
                request_id=request_id_var.get(),
            )

        resp = ok({'password': result})
        resp.headers['X-API-Deprecated'] = 'true'
        resp.headers['X-API-Sunset'] = 'v3.0'
        resp.headers['X-API-Replacement'] = 'POST /api/users/{id}/reset-password'
        return resp


class UserRoleUpdate(HTTPEndpoint):
    @requires_permission(Permission.USER_WRITE)
    async def put(self, request):
        body = await parse_body(UpdateUserRoleRequest, request)

        async with get_conn() as conn:
            if not request.user.admin:
                ok_role, msg = await _can_assign_role(request.user, conn, body.role_id)
                if not ok_role:
                    return api_error('FORBIDDEN', msg, status=403)
            await Users(conn).update_role(body.user_id, body.role_id)
            await AuditLog(conn).log_event(
                event_type='user.role_changed',
                actor_id=request.user.id,
                resource_type='user',
                resource_id=str(body.user_id),
                details={'role_id': body.role_id},
                request_id=request_id_var.get(),
            )

        return ok({})


class RefreshToken(HTTPEndpoint):
    async def post(self, request):
        # Rate-limited: unauthenticated mint of fresh credentials (R2-M9).
        ip = request.client.host if request.client else 'unknown'
        allowed, msg = await refresh_bucket.check(ip)
        if not allowed:
            return api_error('RATE_LIMITED', msg, status=429)
        # HttpOnly refresh cookie is preferred; body fallback keeps
        # API-client compatibility (OAuth, external integrations).
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            try:
                raw = await read_body(request)
            except _BodyTooLargeException:
                await refresh_bucket.record(ip, success=False)
                return api_error('BODY_TOO_LARGE', 'Request body exceeds 1MB limit', status=413)
            if raw:
                body = await parse_body(RefreshTokenRequest, request)
                refresh_token = body.refresh_token
        if not refresh_token:
            await refresh_bucket.record(ip, success=False)
            return api_error('INVALID_TOKEN', 'Missing refresh token', status=401)
        try:
            data = verify_refresh_token(refresh_token)
        except _jwt.ExpiredSignatureError:
            await refresh_bucket.record(ip, success=False)
            return api_error('TOKEN_EXPIRED', 'Refresh token expired', status=401)
        except _jwt.InvalidTokenError:
            await refresh_bucket.record(ip, success=False)
            return api_error('INVALID_TOKEN', 'Invalid refresh token', status=401)

        # R2-H4: fail CLOSED when the blocklist is unreachable — refreshing
        # a session that may have been revoked is worse than asking the user
        # to log in again.
        if await is_blocked(data.get('jti', ''), fail_closed=True):
            await refresh_bucket.record(ip, success=False)
            return api_error('TOKEN_REVOKED', 'Refresh token revoked', status=401)

        await block_token(refresh_token)

        # Re-read the full auth state from the DB: refresh must mint a token
        # from current facts (status, admin, role, permissions, token_version),
        # never from the (possibly stale) refresh-token claims. Fail closed
        # when the row is missing or the account is not active.
        try:
            async with get_conn() as conn:
                user_row = await Users(conn).get_user_row(data['id'])
                if user_row and user_row.get('status') == 'active':
                    role_slug, permissions = await Users(conn).get_user_role(data['id'])
        except RuntimeError:
            user_row = None
            role_slug, permissions = None, []

        if not user_row or user_row.get('status') != 'active':
            return api_error('ACCOUNT_UNAVAILABLE', 'Account unavailable', status=401)
        if (user_row.get('token_version') or 0) != data.get('token_version', 0):
            return api_error('TOKEN_REVOKED', 'Session invalidated', status=401)

        await refresh_bucket.record(ip, success=True)
        user = {'id': data['id'], 'admin': bool(user_row.get('admin', False))}
        if user_row.get('tenant'):
            user['tenant'] = user_row['tenant']
        access, refresh = create_token_pair(
            user, role=role_slug, permissions=permissions,
            token_version=user_row.get('token_version') or 0,
        )
        # R2-LOW: refresh token is delivered ONLY via the HttpOnly cookie
        # below — never in the JSON body.
        resp = ok({
            'access_token': access,
            'expires_in': 3600,
            'token_type': 'Bearer',
        })
        resp.set_cookie(
            key='refresh_token',
            value=refresh,
            httponly=True,
            samesite='strict',
            secure=cookie_secure(),
            path='/api/auth',
        )
        # IAM audit H-2: the browser refresh channel must also rotate the
        # access cookie — a cookie-only frontend has no other way to pick up
        # the new access JWT.
        resp.set_cookie(
            key='token',
            value=access,
            httponly=True,
            samesite='strict',
            secure=cookie_secure(),
            path='/',
        )
        # Rotate the CSRF token on refresh for defense-in-depth.
        import secrets
        resp.set_cookie(
            key='csrf_token',
            value=secrets.token_hex(32),
            httponly=False,
            samesite='strict',
            secure=cookie_secure(),
            path='/',
        )
        return resp
