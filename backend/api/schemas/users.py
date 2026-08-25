from typing import Literal

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(description="Unique username for the new user")
    admin: bool = Field(False, description="Grant superadmin privileges")
    role_id: str | None = Field(None, description="UUID of the role to assign")


class UserActionRequest(BaseModel):
    id: int = Field(description="User database ID to act on")


class BatchUserStatusRequest(BaseModel):
    # ADM-02 bulk operations (§2.10): status vocabulary matches the users
    # table ('active' | 'deactivated'), not a new 'inactive' state.
    user_ids: list[int] = Field(
        min_length=1, max_length=200,
        description="User database IDs to transition in one audited call",
    )
    target_status: Literal['active', 'deactivated'] = Field(
        description="Target account status for every listed user",
    )


class UpdateUserRoleRequest(BaseModel):
    user_id: int = Field(description="User database ID")
    role_id: int | None = Field(None, description="New role UUID (null to remove role)")
