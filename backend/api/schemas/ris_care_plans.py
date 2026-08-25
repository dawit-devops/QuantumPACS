"""Pydantic v2 schemas for care plans (CS5/CC-02)."""

from pydantic import BaseModel, Field, field_validator

CARE_PLAN_STATUSES = ('active', 'completed', 'on_hold')


class CarePlanTask(BaseModel):
    label: str = Field(..., min_length=1, max_length=256)
    done: bool = False


class CarePlanRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=256)
    status: str = Field('active', max_length=16)
    tasks: list[CarePlanTask] = Field(default_factory=list)
    responsible_provider: str = Field('', max_length=128)
    follow_up_at: str | None = Field(None, max_length=64)
    notes: str = Field('', max_length=4000)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in CARE_PLAN_STATUSES:
            raise ValueError(f'status must be one of {CARE_PLAN_STATUSES}')
        return v
