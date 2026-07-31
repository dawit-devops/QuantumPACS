from starlette.endpoints import HTTPEndpoint

from api.response import ok, paginated, api_error

import jwt as _jwt

from api.rbac import requires_permission
from api.permissions import Permission
from api.tokens import create_token_pair, verify_refresh_token, block_token, is_blocked
from api.ratelimit import login_bucket, password_bucket
from api.validate import parse_body
from api.schemas.auth import LoginRequest
from api.schemas.account import ChangePasswordRequestV2
from api.schemas.auth_refresh import RefreshTokenRequest, RevokeTokenRequest
from api.schemas.users import CreateUserRequest, UserActionRequest, UpdateUserRoleRequest
from db.conn import get_conn
from db.users import Users
from exceptions import ApiException
from services.interfaces import AuthService


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
    return auth


class Login(HTTPEndpoint):
    async def post(self, request):
        ip = request.client.host if request.client else 'unknown'
        allowed, msg = await login_bucket.check(ip)
        if not allowed:
            return api_error('RATE_LIMITED', msg, status=429)

        body = await parse_body(LoginRequest, request)

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
                    return api_error('AUTH_FAILED', str(e), status=401)

        async with get_conn() as conn:
            await login_bucket.record_db(ip, conn, success=True)
            await Users(conn).update_last_login(data['id'])
            role_slug, permissions = await Users(conn).get_user_role(data['id'])
            access, refresh = create_token_pair(data, role=role_slug, permissions=permissions)
            resp = ok({
                'id': data['id'],
                'admin': data['admin'],
                'role': role_slug or '',
                'permissions': permissions or [],
                'token': access,
                'access_token': access,
                'refresh_token': refresh,
            })
            resp.set_cookie(
                key='token',
                value=access,
                httponly=True,
                samesite='strict',
                secure=True,
                path='/api',
            )
            # Refresh token travels only as an HttpOnly cookie scoped to the
            # refresh endpoint, never in localStorage or URLs.
            resp.set_cookie(
                key='refresh_token',
                value=refresh,
                httponly=True,
                samesite='strict',
                secure=True,
                path='/api/auth/refresh',
            )
            return resp


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
        resp.delete_cookie('token', path='/api')
        resp.delete_cookie('refresh_token', path='/api/auth/refresh')
        return resp


class RevokeToken(HTTPEndpoint):
    @requires_permission(Permission.USER_ADMIN)
    async def post(self, request):
        body = await parse_body(RevokeTokenRequest, request)
        await block_token(body.token)
        return ok({'message': 'Token revoked'})


class UsersHandler(HTTPEndpoint):
    @requires_permission(Permission.USER_READ)
    async def get(self, request):
        q = request.query_params.get('q')
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 20))

        async with get_conn() as conn:
            data = await Users(conn).get_users(offset=offset, limit=limit, username=q)
            total = await Users(conn).count_users(username=q)

        return paginated(
            [Users.to_json(u) for u in data],
            total=total, page=(offset // limit) + 1, per_page=limit,
            request=request,
        )

    @requires_permission(Permission.USER_WRITE)
    async def post(self, request):
        body = await parse_body(CreateUserRequest, request)

        async with get_conn() as conn:
            result = await Users(conn).add_user(body.username, body.admin, role_id=body.role_id)

        return ok({'password': result['password'], 'username': body.username})


class UsersDeactivate(HTTPEndpoint):
    @requires_permission(Permission.USER_DELETE)
    async def post(self, request):
        body = await parse_body(UserActionRequest, request)

        async with get_conn() as conn:
            await Users(conn).deactivate(body.id)

        resp = ok({})
        resp.headers['X-API-Deprecated'] = 'true'
        resp.headers['X-API-Sunset'] = 'v3.0'
        resp.headers['X-API-Replacement'] = 'DELETE /api/users/{id}'
        return resp


class UsersNewPassword(HTTPEndpoint):
    @requires_permission(Permission.USER_WRITE)
    async def post(self, request):
        body = await parse_body(UserActionRequest, request)

        async with get_conn() as conn:
            result = await Users(conn).new_pswd(body.id)

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
            await Users(conn).update_role(body.user_id, body.role_id)

        return ok({})


class RefreshToken(HTTPEndpoint):
    async def post(self, request):
        # HttpOnly refresh cookie is preferred; body fallback keeps
        # API-client compatibility (OAuth, external integrations).
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            body = await parse_body(RefreshTokenRequest, request)
            refresh_token = body.refresh_token
        if not refresh_token:
            return api_error('INVALID_TOKEN', 'Missing refresh token', status=401)
        try:
            data = verify_refresh_token(refresh_token)
        except _jwt.ExpiredSignatureError:
            return api_error('TOKEN_EXPIRED', 'Refresh token expired', status=401)
        except _jwt.InvalidTokenError:
            return api_error('INVALID_TOKEN', 'Invalid refresh token', status=401)

        if await is_blocked(data.get('jti', '')):
            return api_error('TOKEN_REVOKED', 'Refresh token revoked', status=401)

        await block_token(refresh_token)

        try:
            async with get_conn() as conn:
                token_version = await Users(conn).get_token_version(data['id'])
        except RuntimeError:
            token_version = 0

        user = {'id': data['id'], 'admin': data.get('admin', False)}
        if data.get('tenant'):
            user['tenant'] = data['tenant']
        access, refresh = create_token_pair(user, token_version=token_version)
        resp = ok({
            'access_token': access,
            'refresh_token': refresh,
            'expires_in': 3600,
            'token_type': 'Bearer',
        })
        resp.set_cookie(
            key='refresh_token',
            value=refresh,
            httponly=True,
            samesite='strict',
            secure=True,
            path='/api/auth/refresh',
        )
        return resp
