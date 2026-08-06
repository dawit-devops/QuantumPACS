from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error
from api.validate import parse_body
from db.conn import get_conn
from db.api_keys import ApiKeys
from pydantic import BaseModel
from starlette.endpoints import HTTPEndpoint


class CreateApiKeyRequest(BaseModel):
    name: str
    service_name: str
    permissions: list[str] = []
    expires_in_days: int | None = None


def _validate_key_permissions(user, requested: list[str]) -> tuple[bool, str]:
    """Service keys must never out-scope their creator.

    The legacy '*' wildcard means full platform super-admin — no API key may
    carry it. Non-platform admins may only grant a subset of their own
    effective permissions (rbac.py honors the same set).
    """
    if '*' in requested:
        return False, 'Wildcard permissions are not allowed on API keys'
    if getattr(user, 'admin', False):
        return True, ''
    allowed = set(getattr(user, 'permissions', None) or [])
    if not set(requested) <= allowed:
        return False, 'Requested permissions exceed your own grants'
    return True, ''


class ApiKeysHandler(HTTPEndpoint):
    @requires_permission(Permission.SERVICE_KEY_READ)
    async def get(self, request):
        async with get_conn() as conn:
            keys = await ApiKeys(conn).get_all()
        return ok({'data': keys})

    @requires_permission(Permission.SERVICE_KEY_WRITE)
    async def post(self, request):
        body = await parse_body(CreateApiKeyRequest, request)
        user = request.user
        valid, message = _validate_key_permissions(user, body.permissions)
        if not valid:
            return api_error('FORBIDDEN', message, status=403)
        created_by = user.id if hasattr(user, 'id') and not str(user.id).startswith('svc_') else None
        generated = ApiKeys.generate(
            service_name=body.service_name,
            created_by=created_by,
            expires_in_days=body.expires_in_days,
        )
        expires_at = None
        if body.expires_in_days:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        async with get_conn() as conn:
            key_id = await ApiKeys(conn).store(
                name=body.name,
                key_hash=generated['key_hash'],
                prefix=generated['prefix'],
                service_name=body.service_name,
                permissions=body.permissions,
                created_by=created_by,
                expires_at=expires_at,
            )
        return created({
            'id': key_id,
            'raw_key': generated['raw_key'],
            'name': body.name,
            'service_name': body.service_name,
            'permissions': body.permissions,
        })


class ApiKeyHandler(HTTPEndpoint):
    @requires_permission(Permission.SERVICE_KEY_READ)
    async def get(self, request):
        key_id = request.path_params['id']
        async with get_conn() as conn:
            key = await ApiKeys(conn).get(key_id)
        if not key:
            return not_found('API key not found')
        return ok(key)

    @requires_permission(Permission.SERVICE_KEY_DELETE)
    async def delete(self, request):
        key_id = request.path_params['id']
        async with get_conn() as conn:
            existing = await ApiKeys(conn).get(key_id)
            if not existing:
                return not_found('API key not found')
            await ApiKeys(conn).revoke(key_id)
        return ok({})
