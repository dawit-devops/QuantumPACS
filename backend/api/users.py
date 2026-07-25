from starlette.endpoints import HTTPEndpoint

from api.response import ok, paginated, api_error
from datetime import datetime, timezone

import jwt as _jwt

from api.rbac import requires_permission
from api.permissions import Permission
from api.tokens import create_token as gen_token, create_token_pair, verify_refresh_token, block_token, is_blocked
from api.ratelimit import login_bucket
from api.validate import parse_body
from api.schemas.auth import LoginRequest, ChangePasswordRequest
from api.schemas.auth_refresh import RefreshTokenRequest, RevokeTokenRequest
from api.schemas.users import CreateUserRequest, UserActionRequest
from db.conn import get_conn
from db.users import Users
from exceptions import ApiException


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

        async with get_conn() as conn:
            try:
                data = await Users(conn).login(body.username, body.password)
            except ApiException as e:
                await login_bucket.record_db(ip, conn, success=False)
                return api_error('AUTH_FAILED', str(e), status=401)

            await login_bucket.record_db(ip, conn, success=True)
            role_slug, permissions = await Users(conn).get_user_role(data['id'])
            token = gen_token(data, role=role_slug, permissions=permissions)
            resp = ok({
                'id': data['id'],
                'admin': data['admin'],
                'role': role_slug or '',
                'permissions': permissions or [],
                'token': token,
            })
            resp.set_cookie(
                key='token',
                value=token,
                httponly=True,
                samesite='strict',
                path='/api',
            )
            return resp


class ChangePassword(HTTPEndpoint):
    async def post(self, request):
        body = await parse_body(ChangePasswordRequest, request)

        async with get_conn() as conn:
            try:
                data = await Users(conn).change_password(request.user, body.password)
            except ApiException as e:
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
        return ok({'message': 'Logged out'})


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
            result = await Users(conn).add_user(body.username, body.admin)

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


class RefreshToken(HTTPEndpoint):
    async def post(self, request):
        body = await parse_body(RefreshTokenRequest, request)
        try:
            data = verify_refresh_token(body.refresh_token)
        except _jwt.ExpiredSignatureError:
            return api_error('TOKEN_EXPIRED', 'Refresh token expired', status=401)
        except _jwt.InvalidTokenError:
            return api_error('INVALID_TOKEN', 'Invalid refresh token', status=401)

        if await is_blocked(data.get('jti', '')):
            return api_error('TOKEN_REVOKED', 'Refresh token revoked', status=401)

        await block_token(body.refresh_token)

        expires = int(datetime.now(timezone.utc).timestamp()) + 86400 * 14
        user = {'id': data['id'], 'admin': data.get('admin', False)}
        if data.get('tenant'):
            user['tenant'] = data['tenant']
        access, refresh = create_token_pair(user)
        return ok({
            'access_token': access,
            'refresh_token': refresh,
            'expires_in': 3600,
            'token_type': 'Bearer',
        })
