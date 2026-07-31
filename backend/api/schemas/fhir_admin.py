from pydantic import BaseModel, Field


class FhirConfigUpdate(BaseModel):
    enabled: bool | None = None
    base_url: str | None = None
    publisher: str | None = None
    max_search_results: int | None = None
    log_retention_days: int | None = None


class FhirClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ''
    redirect_uris: str = ''
    grant_type: str = 'client_credentials'


class FhirClientUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    redirect_uris: str | None = None
    grant_type: str | None = None
    active: bool | None = None
