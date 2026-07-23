from starlette.endpoints import HTTPEndpoint

from api.response import ok, validation_error
from api.tokens import create_token as gen_token
from api.utils import is_admin
from db.conn import get_conn
from db.users import Users
from exceptions import ApiException


class Login(HTTPEndpoint):
    async def post(self, request):
        data = await request.json()

        async with get_conn() as conn:
            try:
                data = await Users(conn).login(data['username'], data['password'])
            except ApiException as e:
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
        q = request.path_params.get('q')
        offset = request.path_params.get('offset')
        limit = request.path_params.get('limit')

        async with get_conn() as conn:
            data = await Users(conn).get_users(offset=offset, limit=limit, username=q)

        return ok({'data': [Users.to_json(u) for u in data]})

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

        return ok({})


class UsersNewPassword(HTTPEndpoint):
    async def post(self, request):
        is_admin(request)
        data = await request.json()

        async with get_conn() as conn:
            result = await Users(conn).new_pswd(data['id'])

        return ok({'password': result})
