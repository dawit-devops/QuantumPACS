"""Pydantic v2 schemas for prior authorization (R2-01).

Status literals mirror the ris_prior_auth_requests CHECK constraint.
"""
from pydantic import BaseModel, Field, field_validator

PRIOR_AUTH_ACTIONS = ('approve', 'deny')


class SubmitPriorAuthRequest(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=64)
    procedure_code: str = Field('', max_length=100)
    payer_id: str = Field('', max_length=50)
    payer_name: str = Field('', max_length=256)


class PriorAuthDecisionRequest(BaseModel):
    action: str = Field(..., min_length=1)
    auth_number: str | None = Field(None, max_length=50)
    approved_units: int | None = None
    approved_date: str | None = None
    expiry_date: str | None = None
    denial_reason: str | None = Field(None, max_length=500)

    @field_validator('action')
    @classmethod
    def _valid_action(cls, v):
        if v not in PRIOR_AUTH_ACTIONS:
            raise ValueError(f'action must be one of {PRIOR_AUTH_ACTIONS}')
        return v