from typing import Optional

from pydantic import BaseModel, Field


class RoutingRuleRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Rule name for display and identification")
    description: Optional[str] = Field('', description="Human-readable rule description")
    conditions: str | dict = Field(default='{}', description="JSON matching conditions for DICOM metadata")
    destination: str = Field(..., min_length=1, description="Target storage replica ID or URL")
    priority: Optional[int] = Field(0, description="Evaluation priority (lower = evaluated first)")
    enabled: Optional[bool] = Field(True, description="Whether the rule is active")
