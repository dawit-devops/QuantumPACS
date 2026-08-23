from typing import Literal

from pydantic import BaseModel, Field


class CreateScopeRequest(BaseModel):
    patient_id: str = Field(description="Primary patient identifier (MRN)")
    scope_type: Literal['ward', 'care_team', 'assigned'] = Field(
        'ward', description="Kind of patient-staff link (minimum necessary scope)"
    )


class CreateFollowUpRequest(BaseModel):
    report_id: str | None = Field(None, description="Report the follow-up references (optional)")
    exam_id: str | None = Field(None, description="Exam the follow-up references (optional)")
    patient_id: str = Field(description="Primary patient identifier (MRN)")
    reason: str = Field(min_length=1, description="Clinical reason for the follow-up")
    priority: Literal['routine', 'stat'] = Field('routine', description="Follow-up priority")
    contact_method: Literal['phone', 'email'] | None = Field(
        None, description="Preferred contact method (P-05)"
    )
    note: str | None = Field(None, max_length=500,
                             description="Free-text note for the coordinator (P-05)")
    preferred_time: str | None = Field(None, max_length=50,
                                       description="Preferred contact time window (P-05)")


class UpdateFollowUpRequest(BaseModel):
    status: Literal['submitted', 'acknowledged', 'completed', 'cancelled'] = Field(
        description="New follow-up status"
    )


class UpdateConsentRequest(BaseModel):
    consent_results: bool = Field(
        description="Patient consent to share results via the portal"
    )
