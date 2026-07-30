from pydantic import BaseModel, Field
from typing import Optional


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    events: list[str] = Field(default_factory=list)
    secret: str = ''
    active: bool = True
    retry_count: int = 3
    timeout_ms: int = 5000


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None
    active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout_ms: Optional[int] = None
