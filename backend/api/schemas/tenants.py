from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str = Field(description="Display name for the tenant organization")
    slug: str = Field(
        pattern=r'^[a-z0-9_][a-z0-9_-]{0,62}$',
        description="URL-safe unique tenant identifier (lowercase letters, digits, underscore; 1-63 chars)",
    )
    domain: str | None = Field(None, description="Domain name for automatic tenant routing")
    db_name: str | None = Field(
        None,
        pattern=r'^[a-z0-9_]{1,63}$',
        description="Dedicated database name for tenant isolation",
    )
    db_host: str | None = Field(None, description="Database host for tenant-specific DB")
    db_port: int | None = Field(None, description="Database port for tenant-specific DB")
    db_user: str | None = Field(None, description="Database user for tenant-specific DB")
    db_password: str | None = Field(None, description="Database password for tenant-specific DB")
    storage_quota_bytes: int = Field(
        0, ge=0,
        description="Storage quota in bytes (0 = unlimited)",
    )
    admin_email: str | None = Field(None, description="Tenant admin contact email")
    plan: str = Field('free', description="Subscription plan slug")


class UpdateTenantRequest(BaseModel):
    name: str | None = Field(None, description="Updated display name")
    domain: str | None = Field(None, description="Updated domain")
    db_host: str | None = Field(None, description="Updated DB host")
    db_port: int | None = Field(None, description="Updated DB port")
    db_user: str | None = Field(None, description="Updated DB user")
    db_password: str | None = Field(None, description="Updated DB password")
    status: str | None = Field(None, description="Tenant status (active/suspended/quarantined/decommissioned)")
    # ge=0: enforcement sites treat quota <= 0 as unlimited, so a negative
    # value here would silently switch throttling off via the audited path.
    storage_quota_bytes: int | None = Field(None, ge=0, description="Updated storage quota")
    # ADM-17: a quota override is only auditable with its reason — required
    # by the handler whenever storage_quota_bytes actually changes.
    quota_justification: str | None = Field(
        None, max_length=1000,
        description="Required when changing the storage quota; stored in the audit event",
    )
    plan: str | None = Field(None, description="Updated subscription plan slug")
