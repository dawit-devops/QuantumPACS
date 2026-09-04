"""Pydantic v2 schemas for RIS order intake (E-RIS-02/03).

Status and priority literals mirror the ris_orders CHECK constraints so a
schema validation error surfaces before a DB constraint violation.
"""
from pydantic import BaseModel, Field, field_validator

ORDER_STATUSES = ('ORDERED', 'SCHEDULED', 'ARRIVED', 'IN_PROGRESS',
                  'COMPLETED', 'READ', 'SIGNED', 'CANCELLED')
PRIORITIES = ('ROUTINE', 'URGENT', 'STAT')
PROCEDURE_STATUSES = ('ORDERED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED')


class OrderProcedureRequest(BaseModel):
    procedure_code: str = Field(..., min_length=1, max_length=20)
    procedure_name: str = Field(..., min_length=1, max_length=256)
    modality: str = Field(..., min_length=1, max_length=10)
    body_part: str | None = Field(None, max_length=100)
    laterality: str | None = Field(None, max_length=10)
    contrast: bool = False
    cpt_code: str | None = Field(None, max_length=10)
    icd10_code: str | None = Field(None, max_length=10)


class CreateOrderRequest(BaseModel):
    accession_number: str = Field(..., min_length=1, max_length=20)
    patient_id: str = Field(..., min_length=1, max_length=64)
    patient_name: str | None = Field(None, max_length=256)
    patient_dob: str | None = Field(None, description='Date of birth YYYY-MM-DD')
    referring_physician: str | None = Field(None, max_length=256)
    clinical_indication: str | None = None
    priority: str = 'ROUTINE'
    procedures: list[OrderProcedureRequest] = Field(default_factory=list)

    @field_validator('priority')
    @classmethod
    def _valid_priority(cls, v):
        if v not in PRIORITIES:
            raise ValueError(f'priority must be one of {PRIORITIES}')
        return v

    @field_validator('patient_dob')
    @classmethod
    def _valid_dob(cls, v):
        # Keep the wire format loose (raw string) so the HL7 engine can pass
        # YYYYMMDD through; only the DB cast validates strictly at insert.
        if v is not None and len(v) > 10:
            raise ValueError('patient_dob must be a date (YYYY-MM-DD or YYYYMMDD)')
        return v


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description='Target order status')
    reason: str | None = Field(None, max_length=512)

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        if v not in ORDER_STATUSES:
            raise ValueError(f'status must be one of {ORDER_STATUSES}')
        return v