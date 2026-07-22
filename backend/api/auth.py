"""Starlette authentication backend — JWT token verification on every API request.
Supports bearer tokens via X-Auth-Pacs header, query parameter tokens for WebSocket,
and shared-file access tokens for expiring share links."""
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, BaseUser,
    AuthCredentials
)
from api.response import unauthorized
from api.tokens import verify_token
from config import config
from db.conn import get_conn
from db.share_files import SharedFiles
from db.users import Users

class User(BaseUser):
    def __init__(self, data):
        self.id = data['id']
        self.admin = data.get('admin', False)

    @property
    def is_authenticated(self):
        return True

    @property
    def display_name(self):
        return str(self.id)

    def to_dict(self):
        return {
            'id': self.id,
            'admin': self.admin,
        }


class TokenAuth(AuthenticationBackend):
    async def authenticate(self, request):
        path = request.url.path
        if not path.startswith('/api'):
            return
        if path == '/api/login':
            return
        if request.scope.get('method') == 'OPTIONS':
            return

        data = None
        if request.url.scheme != 'ws':
            auth = request.headers.get('X-Auth-Pacs')
            if not auth:
                auth = request.query_params.get('token')
                if not auth:
                    raise AuthenticationError('Invalid auth')

            credentials = auth
            try:
                data = verify_token(credentials)
                async with get_conn() as conn:
                    active = await Users(conn).is_active(data['id'])
                if not active:
                    raise AuthenticationError('Deactivated user')

            except Exception as e:
                # try share file key
                async with get_conn() as conn:
                    file_id = await SharedFiles(conn).check(credentials)

                if file_id and (path.startswith(f'/api/files/{file_id}') or path.startswith(f'/api/ws_token')):
                    data = {'id': credentials, 'admin': False}
                else:
                    raise AuthenticationError('Invalid auth')
        else:
            token = request.query_params.get('token')
            try:
                data = verify_token(token)
            except Exception as e:
                raise AuthenticationError('Invalid auth')

            data = {'id': data['id'], 'admin': data['admin']}

        if not data:
            raise AuthenticationError('Invalid auth')

        return AuthCredentials(["authenticated"]), User(data)

    @staticmethod
    def on_auth_error(request, exc):
        return unauthorized(str(exc))
