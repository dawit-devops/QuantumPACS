from typing import Optional

from pydantic import BaseModel, Field


class FhirConfigUpdate(BaseModel):
    enabled: Optional[bool] = Field(None, description="Enable/disable the FHIR server")
    base_url: Optional[str] = Field(None, description="Public base URL for FHIR endpoints")
    publisher: Optional[str] = Field(None, description="Publisher name in CapabilityStatement")
    max_search_results: Optional[int] = Field(None, description="Maximum results per search query")
    log_retention_days: Optional[int] = Field(None, description="Days to retain FHIR audit logs")


class FhirClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="SMART-on-FHIR client name")
    description: str = Field('', description="Client description")
    redirect_uris: str = Field('', description="Space-separated allowed redirect URIs")
    grant_type: str = Field('client_credentials', description="OAuth grant type for this client")


class FhirClientUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated client name")
    description: Optional[str] = Field(None, description="Updated description")
    redirect_uris: Optional[str] = Field(None, description="Updated redirect URIs")
    grant_type: Optional[str] = Field(None, description="Updated grant type")
    active: Optional[bool] = Field(None, description="Updated active status")
