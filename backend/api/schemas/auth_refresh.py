from pydantic import BaseModel


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    token: str
