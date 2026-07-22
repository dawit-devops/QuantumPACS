from pydantic import BaseModel


class FileUpdateRequest(BaseModel):
    tag: dict | None = None
    tools_state: dict | None = None


class ShareRequest(BaseModel):
    duration: int
