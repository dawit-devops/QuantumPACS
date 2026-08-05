from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(description="Unique username for the new user")
    admin: bool = Field(False, description="Grant superadmin privileges")
    role_id: str | None = Field(None, description="UUID of the role to assign")


class UserActionRequest(BaseModel):
    id: int = Field(description="User database ID to act on")


class UpdateUserRoleRequest(BaseModel):
    user_id: int = Field(description="User database ID")
    role_id: int | None = Field(None, description="New role UUID (null to remove role)")
