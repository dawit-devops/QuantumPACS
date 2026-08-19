"""Pydantic v2 schemas for RIS scheduling (S4-06/07).

Resource type and schedule literals mirror the DB CHECK constraints so a
schema validation error surfaces before a DB constraint violation.
"""
from pydantic import BaseModel, Field, field_validator, model_validator

RESOURCE_TYPES = ('ROOM', 'MODALITY', 'TECH')
DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


class CreateResourceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    resource_type: str
    modality: str | None = Field(None, max_length=10)
    location: str | None = Field(None, max_length=128)

    @field_validator('resource_type')
    @classmethod
    def _valid_type(cls, v):
        if v not in RESOURCE_TYPES:
            raise ValueError(f'resource_type must be one of {RESOURCE_TYPES}')
        return v


class CreateScheduleRequest(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., min_length=8, max_length=8)
    end_time: str = Field(..., min_length=8, max_length=8)

    @model_validator(mode='after')
    def _end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class CreateAppointmentRequest(BaseModel):
    order_id: str = Field(default='', max_length=64)
    resource_id: str
    patient_id: str = Field(..., min_length=1, max_length=128)
    start_time: str
    end_time: str
    reason: str = Field('', max_length=500)
    override_reason: str = Field('', max_length=500)


class RescheduleRequest(BaseModel):
    new_start_time: str
    new_end_time: str
    reason: str = Field('', max_length=500)

    @model_validator(mode='after')
    def _end_after_start(self):
        if self.new_end_time <= self.new_start_time:
            raise ValueError('new_end_time must be after new_start_time')
        return self


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1)