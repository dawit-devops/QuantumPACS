from pydantic import BaseModel, Field


class RoutingRuleRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = ''
    conditions: str | dict = Field(default='{}')
    destination: str = Field(..., min_length=1)
    priority: int | None = 0
    enabled: bool | None = True
