"""Request schemas for the §2.11 nursing endpoints.

Physiological ranges are enforced here (422) rather than at the DB so a
fat-fingered vitals entry never lands in the record. Unlike the encounters
schema (which passes raw timestamp strings to SQL), no client timestamps
are accepted anywhere — recorded/signed times are server-side by contract.
"""
from pydantic import BaseModel, Field, field_validator, model_validator


class VitalsRequest(BaseModel):
    bp_systolic: int | None = Field(None, ge=30, le=250)
    bp_diastolic: int | None = Field(None, ge=20, le=150)
    heart_rate: int | None = Field(None, ge=20, le=260)
    spo2: int | None = Field(None, ge=50, le=100)
    temperature_c: float | None = Field(None, ge=30, le=43)
    respiration: int | None = Field(None, ge=4, le=60)
    weight_kg: float | None = Field(None, ge=0, le=500)
    height_cm: float | None = Field(None, ge=0, le=300)


class ChecklistItem(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    required: bool = False
    checked: bool = False


class ChecklistUpdateRequest(BaseModel):
    items: list[ChecklistItem] = Field(min_length=1, max_length=50)
    confirmed: bool = False


class ContrastConsentRequest(BaseModel):
    accepted: bool
    # Kiosk-consent shape: base64 PNG data URL. ~200 KB binary ceiling keeps
    # the 1 MB global body cap comfortable.
    signature_png: str = Field('', max_length=280_000)
    declined_reason: str = Field('', max_length=500)
    consent_text_version: str = Field('', max_length=32)
    witnessed_by: str = Field('', max_length=128)

    @field_validator('signature_png')
    @classmethod
    def _png_data_url(cls, v):
        if v and not v.startswith('data:image/png;base64,'):
            raise ValueError('signature_png must be a base64 PNG data URL')
        return v

    @model_validator(mode='after')
    def _consent_shape_matches_decision(self):
        # Cross-field rules live in a model validator: field-level
        # after-validators are skipped for defaulted fields, and both
        # signature_png/declined_reason default to ''.
        if self.accepted and not self.signature_png:
            raise ValueError(
                'A captured signature is required to accept consent'
            )
        if not self.accepted and not self.declined_reason.strip():
            raise ValueError(
                'A decline reason is required when consent is refused'
            )
        return self


class NurseNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=4000)
