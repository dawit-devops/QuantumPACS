from pydantic import BaseModel, Field, field_validator

from api.permissions import Permission


def _validate_permissions(perms):
    """Reject unknown codes and the wildcard '*' grant.

    has_permission() treats '*' as a full-grant wildcard (legacy token
    fixtures); role schemas must not allow creating roles that bypass
    every permission check (privilege escalation via ROLE_WRITE).
    """
    known = {p.value for p in Permission}
    for code in perms:
        if code == '*':
            raise ValueError("wildcard '*' permission is not allowed on roles")
        if code not in known:
            raise ValueError(f"unknown permission: {code}")
    return perms


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Display name for the role")
    slug: str = Field(min_length=1, max_length=100, pattern=r'^[a-z0-9_]+$', description="URL-safe unique identifier for the role")
    description: str | None = Field(None, max_length=500, description="Human-readable role description")
    permissions: list[str] = Field(default_factory=list, description="List of permission slugs assigned to this role")

    @field_validator('permissions')
    @classmethod
    def check_permissions(cls, v):
        return _validate_permissions(v)


class UpdateRoleRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="Updated display name")
    slug: str | None = Field(None, min_length=1, max_length=100, pattern=r'^[a-z0-9_]+$', description="Updated slug")
    description: str | None = Field(None, max_length=500, description="Updated description")
    permissions: list[str] | None = Field(None, description="Updated permission list")

    @field_validator('permissions')
    @classmethod
    def check_permissions(cls, v):
        return _validate_permissions(v)
