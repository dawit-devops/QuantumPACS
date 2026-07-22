from pydantic import BaseModel


class CreateReplicaRequest(BaseModel):
    type: str
    location: str | None = None
    delay: int = 0
    app_key_id: str | None = None
    app_key: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None


class UpdateReplicaRequest(BaseModel):
    master: bool | None = None
    delay: int | None = None
