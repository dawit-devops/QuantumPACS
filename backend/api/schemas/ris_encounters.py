"""Pydantic v2 schemas for encounters (CS6/CC-03)."""

from pydantic import BaseModel, Field, field_validator

ENCOUNTER_TYPES = ('visit', 'call', 'message', 'fax')


class EncounterRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    encounter_type: str = Field(..., max_length=16)
    summary: str = Field(..., min_length=1, max_length=4000)
    occurred_at: str | None = Field(None, max_length=64)
    linked_order_id: str = Field('', max_length=128)
    linked_report_id: str = Field('', max_length=128)

    @field_validator('encounter_type')
    @classmethod
    def _valid_type(cls, v):
        if v not in ENCOUNTER_TYPES:
            raise ValueError(f'encounter_type must be one of {ENCOUNTER_TYPES}')
        return v
