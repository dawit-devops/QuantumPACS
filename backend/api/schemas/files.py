from pydantic import BaseModel, Field


class FileUpdateRequest(BaseModel):
    tag: dict | None = Field(default=None, max_length=100_000, description="Custom metadata tag (JSON dict)")
    tools_state: dict | None = Field(default=None, max_length=100_000, description="Viewer tools state snapshot (JSON dict)")


class ShareRequest(BaseModel):
    duration: int = Field(description="Share link lifetime in seconds")
