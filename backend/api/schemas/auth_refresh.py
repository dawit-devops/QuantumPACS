from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(description="Refresh token to exchange for a new access token")


class RevokeTokenRequest(BaseModel):
    token: str = Field(description="Token (access or refresh) to revoke")
