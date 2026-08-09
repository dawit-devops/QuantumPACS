from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field


class CreatePatientRequest(BaseModel):
    patient_id: str = Field('', description="External patient identifier (MRN); generated when empty")
    name: str = Field(..., description="Patient full name")
    birth_date: str = Field('', description="Patient date of birth (YYYY-MM-DD)")
    sex: str = Field('', description="Patient sex (M/F/O)")
    meta: dict | None = Field(None, description="Free-form registration metadata")


class CreateVisitRequest(BaseModel):
    patient_id: str = Field(..., description="Patient identifier (MRN)")
    visit_date: date | None = Field(None, description="Visit date (defaults to today)")
    destination_room: str | None = Field(None, description="Destination room for the visit")


class UpdateVisitRequest(BaseModel):
    status: Literal['registered', 'checked_in', 'in_progress', 'complete'] | None = Field(
        None, description="Visit status (registered/checked_in/in_progress/complete)",
    )
    destination_room: str | None = Field(None, description="Destination room")
    hl7_sync_status: Literal['pending', 'synced', 'failed'] | None = Field(
        None, description="HL7 sync status (pending/synced/failed)",
    )


class CreateOrderRequest(BaseModel):
    requested_procedure: str = Field(..., description="Requested imaging procedure")
    indication: str = Field('', description="Clinical indication for the study")
    urgency: Literal['routine', 'urgent', 'stat'] = Field(
        'routine', description="Urgency level (routine/urgent/stat)",
    )
    referring_physician: str = Field('', description="Referring physician name")


# Canonical DICOM modality codes (R5-16). Capacity rows are keyed on this
# vocabulary, so a free-form string would silently miss the capacity
# configuration — the server, not the client, owns the list.
MODALITIES = ['CT', 'MR', 'PET', 'DX', 'US', 'MG', 'FL', 'XA', 'NM']


class CreateAppointmentRequest(BaseModel):
    patient_id: str = Field(..., description="Patient identifier (MRN)")
    visit_id: str | None = Field(None, description="Associated visit id")
    modality: Literal[*MODALITIES] = Field(
        ..., description="DICOM modality (CT, MR, etc.)",
    )
    room: str = Field('', description="Room where the exam takes place")
    technologist: str = Field('', description="Assigned technologist")
    scheduled_date: date = Field(..., description="Appointment date")
    scheduled_time: time = Field(..., description="Appointment start time")


class CreateConsentRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent document")
    status: Literal['required', 'attached', 'missing'] | None = Field(
        None, description="Consent status (required/attached/missing)",
    )
    file_name: str | None = Field(None, description="Attached file name")


class AttachConsentRequest(BaseModel):
    consent_type: str = Field('', description="Consent type to mark attached; falls back to any pending consent")
    file_name: str = Field('', description="Pre-uploaded file name (metadata only)")


class CreateInsuranceRequest(BaseModel):
    policy_number: str = Field('', description="Insurance policy number")
    guarantor_name: str = Field('', description="Guarantor name")
    authorization_status: Literal['none', 'pending', 'approved', 'denied'] = Field(
        'none', description="Authorization status (none/pending/approved/denied)",
    )
    authorization_number: str = Field('', description="Pre-authorization number")
    notes: str = Field('', description="Free-form notes")


class UpdateInsuranceRequest(BaseModel):
    policy_number: str | None = Field(None, description="Insurance policy number")
    guarantor_name: str | None = Field(None, description="Guarantor name")
    authorization_status: Literal['none', 'pending', 'approved', 'denied'] | None = Field(
        None, description="Authorization status (none/pending/approved/denied)",
    )
    authorization_number: str | None = Field(None, description="Pre-authorization number")
    notes: str | None = Field(None, description="Free-form notes")
