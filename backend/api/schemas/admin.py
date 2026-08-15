"""Pydantic v2 schemas for platform-admin ops endpoints (super_admin review)."""

from pydantic import BaseModel, Field, field_validator


class MaintenanceRequest(BaseModel):
    active: bool = Field(description="Turn maintenance mode on (True) or off (False)")
    # Bounded: the reason is written to the audit log and rendered in the
    # maintenance banner — cap length so nothing hostile or huge lands there.
    reason: str = Field(
        default='', min_length=0, max_length=500,
        description="Optional human-readable reason shown in the banner and audit trail",
    )


class ConfigUpdateItem(BaseModel):
    value: str | int | bool = Field(description="New value for the whitelisted key")


class ConfigUpdateRequest(BaseModel):
    # Key allowlist enforced again at the endpoint (defense in depth); the
    # schema keeps values scalar and bounded.
    settings: dict[str, ConfigUpdateItem] = Field(
        default_factory=dict,
        description="Whitelisted key -> new value map",
    )

    @field_validator('settings')
    @classmethod
    def _cap_settings_size(cls, v):
        if len(v) > 50:
            raise ValueError('Too many settings in one request')
        return v


class BackupActionRequest(BaseModel):
    pass  # placeholder for future restore options; delete takes no body
