"""Pydantic v2 schemas for handoff notes (CC-08)."""

from pydantic import BaseModel, Field, field_validator

HANDOFF_PRIORITIES = ('low', 'normal', 'high', 'urgent')


class CreateHandoffNoteRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    note: str = Field(..., max_length=4000)
    priority: str = Field('normal', max_length=16)

    @field_validator('priority')
    @classmethod
    def _valid_priority(cls, v):
        if v not in HANDOFF_PRIORITIES:
            raise ValueError(f'priority must be one of {HANDOFF_PRIORITIES}')
        return v