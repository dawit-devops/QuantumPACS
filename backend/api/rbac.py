import functools

from starlette.exceptions import HTTPException

from .permissions import Permission, BUILT_IN_ROLES
from .response import forbidden


def requires_permission(permission: Permission):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise HTTPException(status_code=401, detail='Not authenticated')
            perms = getattr(user, 'permissions', [])
            if permission.value not in perms:
                return forbidden(f'Missing permission: {permission.value}')
            return await func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def get_role_permissions(role_slug: str | None) -> list[str]:
    if not role_slug:
        return list(BUILT_IN_ROLES.get('cashier', []))
    return list(BUILT_IN_ROLES.get(role_slug, BUILT_IN_ROLES.get('cashier', [])))