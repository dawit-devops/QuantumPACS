from typing import Literal

from pydantic import BaseModel, Field


class CreateReplicaRequest(BaseModel):
    type: Literal['local', 's3', 'b2'] = Field(description="Storage backend type")
    location: str | None = Field(None, description="File path or bucket name for the replica")
    delay: int = Field(0, description="Replication delay in seconds")
    app_key_id: str | None = Field(None, description="Backblaze B2 application key ID")
    app_key: str | None = Field(None, description="Backblaze B2 application key")
    access_key_id: str | None = Field(None, description="AWS S3 access key ID")
    secret_access_key: str | None = Field(None, description="AWS S3 secret access key")


class UpdateReplicaRequest(BaseModel):
    master: bool | None = Field(None, description="Promote/demote this replica as master")
    delay: int | None = Field(None, description="Updated replication delay")
