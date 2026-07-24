from pydantic import BaseModel, Field


class FileUpdateRequest(BaseModel):
    tag: dict | None = Field(default=None, max_length=100_000)
    tools_state: dict | None = Field(default=None, max_length=100_000)


class ShareRequest(BaseModel):
    duration: int
