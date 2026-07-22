from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    username: str
    admin: bool = False


class UserActionRequest(BaseModel):
    id: int
