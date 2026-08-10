from pydantic import BaseModel, Field


class CreateOAuthProviderRequest(BaseModel):
    issuer: str = Field(description="OAuth provider issuer URL")
    client_id: str = Field(description="OAuth client ID registered with the provider")
    client_secret: str = Field('', description="OAuth client secret (encrypted at rest)")
    jwks_uri: str | None = Field(None, description="JWKS URI for token signature verification")
    token_url: str | None = Field(None, description="Token endpoint URL (defaults to issuer/token)")
    redirect_uri: str | None = Field(None, description="Callback redirect URI")
    scope: str = Field('openid email profile', description="OAuth scopes to request")
    groups_claim: str = Field('groups', description="JWT claim containing group membership")
    # R2-M7: IdP group name → role slug. Only groups present in the claim
    # named by groups_claim are consulted; unmapped groups fall through to
    # default_role (JIT provisioning) or leave the stored role untouched.
    groups_map: dict | None = Field(None, description="Mapping of IdP group names to role slugs")
    auto_provision: bool = Field(True, description="Auto-create users on first login")
    enabled: bool = Field(True, description="Whether this provider is active")
    tenant_id: str | None = Field(None, description="Tenant scope for this provider")
    slug: str | None = Field(None, description="URL-safe unique slug for ?idp=<slug> param")
    # R2-H3: least-privilege JIT — self-registering identities get the
    # patient portal role unless the provider explicitly overrides it.
    default_role: str = Field('patient', description="Default role slug for auto-provisioned users")


class UpdateOAuthProviderRequest(BaseModel):
    issuer: str | None = Field(None, description="Updated issuer URL")
    client_id: str | None = Field(None, description="Updated client ID")
    client_secret: str | None = Field(None, description="Updated client secret")
    jwks_uri: str | None = Field(None, description="Updated JWKS URI")
    token_url: str | None = Field(None, description="Updated token URL")
    redirect_uri: str | None = Field(None, description="Updated redirect URI")
    scope: str | None = Field(None, description="Updated scope list")
    groups_claim: str | None = Field(None, description="Updated groups claim name")
    groups_map: dict | None = Field(None, description="Updated IdP group → role slug mapping")
    auto_provision: bool | None = Field(None, description="Updated auto-provision flag")
    enabled: bool | None = Field(None, description="Updated enabled flag")
    tenant_id: str | None = Field(None, description="Updated tenant scope")
    default_role: str | None = Field(None, description="Updated default role")
