"""Notification preference schemas (super_admin review P1-1)."""

from pydantic import BaseModel, Field, field_validator


class NotificationPrefsRequest(BaseModel):
    # event_type -> enabled. Bounded: the catalog is a fixed small set and a
    # hostile client must not be able to bloat the request or the table.
    preferences: dict[str, bool] = Field(
        default_factory=dict,
        description="Event type -> enabled map",
    )

    @field_validator('preferences')
    @classmethod
    def _cap_prefs_size(cls, v):
        if len(v) > 64:
            raise ValueError('Too many preferences in one request')
        for key in v:
            if not isinstance(key, str) or len(key) > 64:
                raise ValueError('Invalid event type key')
        return v
