from typing import Optional
from pydantic import BaseModel, Field


class RoutingRuleRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = ''
    conditions: str | dict = Field(default='{}')
    destination: str = Field(..., min_length=1)
    priority: Optional[int] = 0
    enabled: Optional[bool] = True
