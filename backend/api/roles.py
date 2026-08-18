from starlette.endpoints import HTTPEndpoint
import asyncpg

from api.rbac import requires_permission
from api.permissions import (
    Permission,
    PERMISSION_GROUPS,
    IMMUTABLE_ROLE_SLUGS,
    PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES,
)
from api.response import ok, created, not_found, api_error
from api.validate import parse_body
from api.schemas.roles import CreateRoleRequest, UpdateRoleRequest
from db.audit_log import AuditLog
from db.conn import get_conn
from db.roles import Roles
from db.users import Users
from log import request_id_var
from api.tenant_middleware import effective_tenant


def _permissions_subset_of(caller_perms, target_perms):
    """A non-platform-admin may only create/update roles whose permission
    set is a subset of their own — otherwise ROLE_WRITE becomes a backdoor
    to escalate any role (R2-M2)."""
    return set(target_perms or []) <= set(caller_perms or [])


class RolesHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        async with get_conn() as conn:
            roles = await Roles(conn).get_all()
        # P2-3 (tenant_admin review): tell the Roles page which rows the
        # caller can actually modify, so it can show a lock hint instead of
        # inviting a 403. Immutable anchors and platform-admin-only tiers are
        # locked for everyone below the platform admin; deletion of built-in
        # roles is blocked for every tier (R2-16).
        platform_admin = bool(getattr(request.user, 'admin', False))
        from api.permissions import IMMUTABLE_ROLE_SLUGS, PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES
        for role in roles:
            slug = role.get('slug')
            locked_tier = bool(slug) and (
                slug in IMMUTABLE_ROLE_SLUGS
                or (slug in PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES and not platform_admin)
            )
            role['modifiable'] = not (role.get('built_in') and locked_tier)
        return ok({'data': roles})

    @requires_permission(Permission.ROLE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateRoleRequest, request)
        if not request.user.admin and not _permissions_subset_of(
            request.user.permissions, body.permissions
        ):
            return api_error(
                'FORBIDDEN', 'Role permissions exceed your own grants', status=403
            )
        async with get_conn() as conn:
            try:
                role_id = await Roles(conn).create(
                    name=body.name,
                    slug=body.slug,
                    permissions=body.permissions,
                )
            except asyncpg.UniqueViolationError:
                return api_error(
                    'CONFLICT', f'Slug "{body.slug}" is already in use', status=409
                )
            await AuditLog(conn).log_event(
                event_type='role.created',
                actor_id=request.user.id,
                resource_type='role',
                resource_id=role_id,
                details={'name': body.name, 'slug': body.slug, 'permissions': body.permissions},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'id': role_id})


class RoleHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        role_id = request.path_params['id']
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
        if not role:
            return not_found('Role not found')
        return ok(role)

    @requires_permission(Permission.ROLE_WRITE)
    async def put(self, request):
        role_id = request.path_params['id']
        body = await parse_body(UpdateRoleRequest, request)
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
            if not role:
                return not_found('Role not found')
            if role.get('built_in'):
                # R2-16: built-in roles split into three tiers — immutable
                # (platform/tenant/pacs/emr admin + patient), platform-admin
                # only (teleradiologist), and facility-editable (the remaining
                # clinical/operational slugs). Deletion stays blocked for every
                # built-in; only permission lists are editable.
                slug = role.get('slug')
                if slug in IMMUTABLE_ROLE_SLUGS:
                    return api_error(
                        'FORBIDDEN', 'Cannot modify immutable built-in role', status=403
                    )
                if slug in PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES and not request.user.admin:
                    return api_error(
                        'FORBIDDEN', 'Only the platform admin can modify this role', status=403
                    )
            if (
                body.permissions is not None
                and not request.user.admin
                and not _permissions_subset_of(request.user.permissions, body.permissions)
            ):
                return api_error(
                    'FORBIDDEN', 'Role permissions exceed your own grants', status=403
                )
            try:
                await Roles(conn).patch(
                    role_id,
                    body.model_dump(exclude_none=True),
                )
            except asyncpg.UniqueViolationError:
                return api_error(
                    'CONFLICT', f'Slug "{body.slug}" is already in use', status=409
                )
            if body.permissions is not None:
                await Users(conn).bulk_increment_token_version_by_role(role_id)
            await AuditLog(conn).log_event(
                event_type='role.updated',
                actor_id=request.user.id,
                resource_type='role',
                resource_id=role_id,
                details=body.model_dump(exclude_none=True),
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})

    @requires_permission(Permission.ROLE_DELETE)
    async def delete(self, request):
        role_id = request.path_params['id']
        async with get_conn() as conn:
            role = await Roles(conn).get(role_id)
            if not role:
                return not_found('Role not found')
            if role.get('built_in'):
                return api_error('FORBIDDEN', 'Cannot delete built-in role', status=403)
            await Roles(conn).delete(role_id)
            # Users holding the deleted role lose its grants — bump their
            # token_version so stale JWTs force re-auth on next request.
            await Users(conn).bulk_increment_token_version_by_role(role_id)
            await AuditLog(conn).log_event(
                event_type='role.deleted',
                actor_id=request.user.id,
                resource_type='role',
                resource_id=role_id,
                details={'name': role.get('name'), 'slug': role.get('slug')},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class PermissionsHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        return ok({'data': PERMISSION_GROUPS})


class RoleUsersHandler(HTTPEndpoint):
    @requires_permission(Permission.ROLE_READ)
    async def get(self, request):
        role_id = request.path_params['id']
        async with get_conn() as conn:
            # users has no `active` column — status carries it (default
            # 'active'). Fixes a 500 that made the roles membership modal
            # (P2-5) fail for every role.
            rows = await conn.fetch(
                'SELECT id, username, admin, status FROM users WHERE role_id = $1 ORDER BY username',
                role_id,
            )
        return ok({'data': [dict(r) for r in rows]})
