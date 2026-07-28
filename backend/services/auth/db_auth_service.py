from typing import Any, Optional

from db.conn import get_conn
from db.users import Users
from pypika import Table as PypikaTable
from pypika.dialects import PostgreSQLQuery as Query

from api.rbac import get_role_permissions
from api.tokens import verify_token
from exceptions import ApiException
from services.interfaces import AuthService


_users_table = PypikaTable('users')


class DatabaseAuthService(AuthService):
    def __init__(self, conn_provider=None):
        self._conn_provider = conn_provider or get_conn

    async def _fetchrow(self, q):
        async with self._conn_provider() as conn:
            return await conn.fetchrow(str(q))

    async def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        async with self._conn_provider() as conn:
            users = Users(conn)
            try:
                user = await users.login(username, password)
                return dict(user) if user else None
            except ApiException:
                return None

    async def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        try:
            return verify_token(token)
        except Exception:
            return None

    async def authorize(self, user: dict[str, Any], permission: str) -> bool:
        role_slug = user.get('role_slug') or user.get('role')
        if role_slug is None and user.get('id') is not None:
            async with self._conn_provider() as conn:
                users = Users(conn)
                role_slug, perms = await users.get_user_role(user['id'])
        else:
            perms = get_role_permissions(role_slug)
        return permission in perms

    async def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
        q = Query.from_(_users_table).select('*').where(_users_table.id == user_id)
        row = await self._fetchrow(q)
        return dict(row) if row else None
