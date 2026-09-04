"""Pydantic v2 schemas for referral tracking (CC-05)."""

from pydantic import BaseModel, Field, field_validator

REFERRAL_STATUSES = ('pending', 'accepted', 'completed', 'cancelled')


class CreateReferralRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    from_provider: str = Field('', max_length=256)
    to_specialist: str = Field(..., min_length=1, max_length=256)
    specialty: str = Field('', max_length=128)
    status: str = Field('pending', max_length=16)
    order_id: str = Field('', max_length=64)
    report_id: str = Field('', max_length=64)
    notes: str = Field('', max_length=4000)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in REFERRAL_STATUSES:
            raise ValueError(f'status must be one of {REFERRAL_STATUSES}')
        return v


class UpdateReferralRequest(BaseModel):
    status: str = Field(..., max_length=16)
    notes: str = Field('', max_length=4000)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in REFERRAL_STATUSES:
            raise ValueError(f'status must be one of {REFERRAL_STATUSES}')
        return v