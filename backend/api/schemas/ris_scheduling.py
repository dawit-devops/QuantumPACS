"""Pydantic v2 schemas for RIS scheduling (S4-06/07).

Resource type and schedule literals mirror the DB CHECK constraints so a
schema validation error surfaces before a DB constraint violation.
"""
from datetime import datetime

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
    resource_id: str = Field(..., min_length=1, max_length=64)
    patient_id: str = Field(..., min_length=1, max_length=128)
    start_time: str
    end_time: str
    reason: str = Field('', max_length=500)
    override_reason: str = Field('', max_length=500)
    prep_instructions: str = Field('', max_length=2000)

    @field_validator('start_time', 'end_time')
    @classmethod
    def _valid_datetime(cls, v):
        # B-8: reject malformed datetimes at the schema boundary so the
        # engine/API never see a 500-worthy string.
        try:
            datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError(f'Invalid datetime {v!r}: expected ISO 8601') from exc
        return v

    @model_validator(mode='after')
    def _end_after_start(self):
        start = datetime.fromisoformat(str(self.start_time).replace('Z', '+00:00'))
        end = datetime.fromisoformat(str(self.end_time).replace('Z', '+00:00'))
        if end <= start:
            raise ValueError('end_time must be after start_time')
        return self


class RescheduleRequest(BaseModel):
    new_start_time: str
    new_end_time: str
    reason: str = Field('', max_length=500)

    @field_validator('new_start_time', 'new_end_time')
    @classmethod
    def _valid_datetime(cls, v):
        try:
            datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError(f'Invalid datetime {v!r}: expected ISO 8601') from exc
        return v

    @model_validator(mode='after')
    def _end_after_start(self):
        # Real datetime comparison — string ordering breaks across timezones.
        start = datetime.fromisoformat(str(self.new_start_time).replace('Z', '+00:00'))
        end = datetime.fromisoformat(str(self.new_end_time).replace('Z', '+00:00'))
        if end <= start:
            raise ValueError('new_end_time must be after new_start_time')
        return self


class ScheduleSlot(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., min_length=8, max_length=8)
    end_time: str = Field(..., min_length=8, max_length=8)

    @model_validator(mode='after')
    def _end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slots: list[ScheduleSlot] = Field(..., min_length=1)


class ApplyTemplateRequest(BaseModel):
    resource_id: str = Field(..., min_length=1, max_length=64)


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1)