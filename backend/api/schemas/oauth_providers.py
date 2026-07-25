from pydantic import BaseModel


class CreateOAuthProviderRequest(BaseModel):
    issuer: str
    client_id: str
    client_secret: str = ''
    jwks_uri: str | None = None
    token_url: str | None = None
    redirect_uri: str | None = None
    scope: str = 'openid email profile'
    groups_claim: str = 'groups'
    auto_provision: bool = True
    enabled: bool = True
    tenant_id: str | None = None


class UpdateOAuthProviderRequest(BaseModel):
    issuer: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    jwks_uri: str | None = None
    token_url: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None
    groups_claim: str | None = None
    auto_provision: bool | None = None
    enabled: bool | None = None
    tenant_id: str | None = None
