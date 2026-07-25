from pydantic import BaseModel


class CreateRoleRequest(BaseModel):
    name: str
    slug: str
    permissions: list[str] = []


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    permissions: list[str] | None = None
