from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    events: list[str] = Field(default_factory=list)
    secret: str = ''
    active: bool = True
    retry_count: int = 3
    timeout_ms: int = 5000


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    active: bool | None = None
    retry_count: int | None = None
    timeout_ms: int | None = None
