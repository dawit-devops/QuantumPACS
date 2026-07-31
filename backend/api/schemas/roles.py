from pydantic import BaseModel, Field


class CreateRoleRequest(BaseModel):
    name: str = Field(description="Display name for the role")
    slug: str = Field(description="URL-safe unique identifier for the role")
    description: str | None = Field(None, description="Human-readable role description")
    permissions: list[str] = Field(default_factory=list, description="List of permission slugs assigned to this role")


class UpdateRoleRequest(BaseModel):
    name: str | None = Field(None, description="Updated display name")
    slug: str | None = Field(None, description="Updated slug")
    description: str | None = Field(None, description="Updated description")
    permissions: list[str] | None = Field(None, description="Updated permission list")
