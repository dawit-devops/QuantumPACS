import functools

from starlette.exceptions import HTTPException
from starlette.requests import Request

from .permissions import Permission, BUILT_IN_ROLES
from .response import forbidden

# Canonical §7 permission → legacy codes that still grant access
# (RBAC_matrix_spec.md §7: LOG_READ stays as the alias of AUDIT_READ;
# METRICS_READ is the legacy alias of the canonical ANALYTICS_READ).
# Single source of truth for alias resolution. Keyed by plain string so the
# map works while Stream 1 adds the canonical enum members to permissions.py.
PERMISSION_ALIASES = {
    'AUDIT_READ': ('LOG_READ',),
    'ANALYTICS_READ': ('METRICS_READ',),
}

# Reverse index: legacy code → canonical codes that alias it. Guards written
# against the legacy codes (e.g. api/logs.py checks Permission.LOG_READ) must
# accept a user who holds only the canonical grant, so resolution is
# symmetric: LOG_READ ⇄ AUDIT_READ, METRICS_READ ⇄ ANALYTICS_READ.
PERMISSION_ALIASES_REVERSE = {}
for _canonical, _aliases in PERMISSION_ALIASES.items():
    for _alias in _aliases:
        PERMISSION_ALIASES_REVERSE.setdefault(_alias, set()).add(_canonical)


def has_permission(user, permission) -> bool:
    """True if `user` holds `permission` (canonical §7 code) or an alias of it.

    `permission` may be a Permission enum member or a plain code string
    (canonical codes enter the enum once Stream 1 ships them, so guard
    callers and tests pass either).
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    code = permission.value if isinstance(permission, Permission) else str(permission)
    perms = set(getattr(user, 'permissions', None) or [])
    if '*' in perms:
        # legacy super-admin wildcard grant (token fixtures, seeded admins)
        return True
    if code in perms:
        return True
    aliases = set(PERMISSION_ALIASES.get(code, ()))
    aliases |= PERMISSION_ALIASES_REVERSE.get(code, set())
    return any(alias in perms for alias in aliases)


def requires_permission(permission):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise HTTPException(status_code=401, detail='Not authenticated')
            if not has_permission(user, permission):
                code = permission.value if isinstance(permission, Permission) else str(permission)
                return forbidden(f'Missing permission: {code}')
            return await func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def guard_endpoint_method(handler_cls, method, permission):
    """Route-level permission guard for a single HTTP method of an HTTPEndpoint.

    Used at wiring time (routes.py) for §7-mapped methods whose handler module
    is owned by another stream and cannot be edited here (files.py). Only the
    named method is checked; all other methods keep the class's own behavior.
    HTTPEndpoint.dispatch sends responses itself, so denied responses must be
    sent here rather than returned (Starlette >= 0.35 contract).
    """
    method = 'get' if method.lower() == 'head' else method.lower()
    guards = {method: permission}

    async def _guarded_dispatch(self):
        request = Request(self.scope, receive=self.receive)
        method_key = 'get' if request.method == 'HEAD' else request.method.lower()
        guard = guards.get(method_key)
        if guard is not None:
            user = request.user
            if not user.is_authenticated:
                raise HTTPException(status_code=401, detail='Not authenticated')
            if not has_permission(user, guard):
                code = guard.value if isinstance(guard, Permission) else str(guard)
                response = forbidden(f'Missing permission: {code}')
                await response(self.scope, self.receive, self.send)
                return
        await handler_cls.dispatch(self)

    return type(
        f'Guarded{handler_cls.__name__}',
        (handler_cls,),
        {'dispatch': _guarded_dispatch},
    )


def get_role_permissions(role_slug: str | None) -> list[str]:
    if not role_slug:
        return list(BUILT_IN_ROLES.get('cashier', []))
    return list(BUILT_IN_ROLES.get(role_slug, BUILT_IN_ROLES.get('cashier', [])))
