from starlette.endpoints import HTTPEndpoint

from api.response import ok, paginated, validation_error
from api.tokens import create_token as gen_token
from api.utils import is_admin
from api.ratelimit import login_bucket
from db.conn import get_conn
from db.users import Users
from exceptions import ApiException


class Login(HTTPEndpoint):
    async def post(self, request):
        ip = request.client.host if request.client else 'unknown'
        allowed, msg = login_bucket.check(ip)
        if not allowed:
            return validation_error(msg)

        data = await request.json()

        async with get_conn() as conn:
            try:
                data = await Users(conn).login(data['username'], data['password'])
            except ApiException as e:
                login_bucket.record(ip)
                return validation_error(str(e))

            token = gen_token(data)
            resp = ok({
                'id': data['id'],
                'admin': data['admin'],
                'token': token,
            })
            return resp


class ChangePassword(HTTPEndpoint):
    async def post(self, request):
        data = await request.json()

        async with get_conn() as conn:
            try:
                data = await Users(conn).change_password(request.user, data['password'])
            except ApiException as e:
                return validation_error(str(e))

            return ok({})


class UsersHandler(HTTPEndpoint):
    async def get(self, request):
        is_admin(request)
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

    async def post(self, request):
        is_admin(request)
        data = await request.json()

        async with get_conn() as conn:
            result = await Users(conn).add_user(data['username'], data['admin'])

        return ok({'password': result['password'], 'username': data['username']})


class UsersDeactivate(HTTPEndpoint):
    async def post(self, request):
        is_admin(request)
        data = await request.json()

        async with get_conn() as conn:
            await Users(conn).deactivate(data['id'])

        resp = ok({})
        resp.headers['X-API-Deprecated'] = 'true'
        resp.headers['X-API-Sunset'] = 'v3.0'
        resp.headers['X-API-Replacement'] = 'DELETE /api/users/{id}'
        return resp


class UsersNewPassword(HTTPEndpoint):
    async def post(self, request):
        is_admin(request)
        data = await request.json()

        async with get_conn() as conn:
            result = await Users(conn).new_pswd(data['id'])

        resp = ok({'password': result})
        resp.headers['X-API-Deprecated'] = 'true'
        resp.headers['X-API-Sunset'] = 'v3.0'
        resp.headers['X-API-Replacement'] = 'POST /api/users/{id}/reset-password'
        return resp
