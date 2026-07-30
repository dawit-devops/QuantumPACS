from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    username: str
    admin: bool = False
    role_id: str | None = None


class UserActionRequest(BaseModel):
    id: int


class UpdateUserRoleRequest(BaseModel):
    user_id: int
    role_id: int | None = None
