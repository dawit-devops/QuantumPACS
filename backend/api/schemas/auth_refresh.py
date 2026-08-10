from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    # Bounded (R2-M6): a refresh token is a few hundred bytes; anything near
    # 4KB is abuse (base64-padded garbage), not a legitimate credential.
    refresh_token: str = Field(default='', max_length=4096, description="Refresh token to exchange for a new access token")


class RevokeTokenRequest(BaseModel):
    token: str = Field(description="Token (access or refresh) to revoke")
