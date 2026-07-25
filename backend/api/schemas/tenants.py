from pydantic import BaseModel


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    domain: str | None = None
    db_name: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_user: str | None = None
    db_password: str | None = None
    storage_quota_bytes: int = 0
    admin_email: str | None = None


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    domain: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_user: str | None = None
    db_password: str | None = None
    status: str | None = None
    storage_quota_bytes: int | None = None
