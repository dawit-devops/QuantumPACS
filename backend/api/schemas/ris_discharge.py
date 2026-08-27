"""Pydantic v2 schemas for discharge planning checklists (CC-06)."""

from pydantic import BaseModel, Field, field_validator

DISCHARGE_STATUSES = ('open', 'completed')

DEFAULT_DISCHARGE_ITEMS = [
    {'label': 'Follow-up appointment scheduled', 'done': False},
    {'label': 'Medication reconciliation', 'done': False},
    {'label': 'Patient education provided', 'done': False},
]


class DischargeItem(BaseModel):
    label: str = Field(..., min_length=1, max_length=256)
    done: bool = False


class CreateDischargeChecklistRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field('Discharge Checklist', max_length=256)
    status: str = Field('open', max_length=16)
    items: list[DischargeItem] = Field(default_factory=list)
    notes: str = Field('', max_length=4000)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in DISCHARGE_STATUSES:
            raise ValueError(f'status must be one of {DISCHARGE_STATUSES}')
        return v


class UpdateDischargeChecklistRequest(BaseModel):
    status: str = Field(..., max_length=16)
    items: list[DischargeItem] = Field(default_factory=list)
    notes: str = Field('', max_length=4000)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in DISCHARGE_STATUSES:
            raise ValueError(f'status must be one of {DISCHARGE_STATUSES}')
        return v