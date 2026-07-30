from typing import Optional

from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable webhook name")
    url: str = Field(..., min_length=1, description="Target URL to receive webhook POST requests")
    events: list[str] = Field(default_factory=list, description="Event types that trigger this webhook")
    secret: str = Field('', description="Shared secret for HMAC signature verification")
    active: bool = Field(True, description="Whether the webhook is enabled")
    retry_count: int = Field(3, description="Number of retries on delivery failure")
    timeout_ms: int = Field(5000, description="HTTP request timeout in milliseconds")


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated webhook name")
    url: Optional[str] = Field(None, description="Updated target URL")
    events: Optional[list[str]] = Field(None, description="Updated event type list")
    secret: Optional[str] = Field(None, description="Updated shared secret")
    active: Optional[bool] = Field(None, description="Updated active flag")
    retry_count: Optional[int] = Field(None, description="Updated retry count")
    timeout_ms: Optional[int] = Field(None, description="Updated timeout in milliseconds")
