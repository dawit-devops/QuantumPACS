from pydantic import BaseModel, Field
from typing import Optional


class FhirConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    publisher: Optional[str] = None
    max_search_results: Optional[int] = None
    log_retention_days: Optional[int] = None


class FhirClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ''
    redirect_uris: str = ''
    grant_type: str = 'client_credentials'


class FhirClientUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    redirect_uris: Optional[str] = None
    grant_type: Optional[str] = None
    active: Optional[bool] = None
