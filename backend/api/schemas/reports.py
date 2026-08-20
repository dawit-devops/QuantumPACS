from pydantic import BaseModel, Field, field_validator


class SaveReportRequest(BaseModel):
    findings: str = Field('', description="Structured findings text")
    impression: str = Field('', description="Impression/conclusion text")
    recommendations: str = Field('', description="Recommendations (optional)")
    template_name: str = Field('', description="Template that seeded the draft")
    status: str = Field('draft', description="draft/preliminary (never final)")

    @field_validator('status')
    @classmethod
    def _valid_status(cls, v):
        # CR-4: `final` is reachable only through the sign endpoint
        # (REPORT_SIGN). Accepting it here would let a writer with only
        # REPORT_WRITE flip a report to final, bypassing the sign gate.
        if v not in ('draft', 'preliminary'):
            raise ValueError('status must be draft or preliminary (final requires signing)')
        return v


class SignReportRequest(BaseModel):
    # Signing requires an impression; the endpoint enforces it server-side.
    confirm: bool = Field(True, description="Explicit sign confirmation")


class ReturnReportRequest(BaseModel):
    # The attending's revision feedback — required, shown to the resident
    # author in their console alert.
    feedback: str = Field('', description="Attending feedback for the resident")
    confirm: bool = Field(True, description="Explicit return confirmation")


class AssignRadiologistRequest(BaseModel):
    radiologist_id: str = Field('', description="User id to assign; empty = assign the requesting user")


class CreatePeerReviewRequest(BaseModel):
    report_id: str = Field(..., description="Report to review")
    reviewer_id: str = Field(..., description="User id of the peer reviewer")


class SubmitPeerReviewRequest(BaseModel):
    discrepancy_level: str = Field(..., description="none/minor/major/discrepancy")
    comment: str = Field('', description="Review comment / feedback")

    @field_validator('discrepancy_level')
    @classmethod
    def _valid_level(cls, v):
        if v not in ('none', 'minor', 'major', 'discrepancy'):
            raise ValueError('discrepancy_level must be none/minor/major/discrepancy')
        return v
