from pydantic import BaseModel, Field, field_validator


class SaveReportRequest(BaseModel):
    findings: str = Field('', description="Structured findings text")
    impression: str = Field('', description="Impression/conclusion text")
    recommendations: str = Field('', description="Recommendations (optional)")
    clinical_history: str = Field('', description="Clinical history / indication")
    technique: str = Field('', description="Acquisition / sequence technique")
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


class ReportImageRequest(BaseModel):
    image_data: str = Field(..., description="data: URL (base64 PNG) captured from the viewer")
    caption: str = Field('', description="Optional caption for the representative image")
    position: int | None = Field(None, ge=0, le=2, description="Slot 0-2; default appends")


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


class DeclinePeerReviewRequest(BaseModel):
    reason: str = Field('', description="Reason for declining the review assignment")


class PublishTemplateRequest(BaseModel):
    findings: str = Field('', description="Findings section body")
    impression: str = Field('', description="Impression section body")


class RollbackTemplateRequest(BaseModel):
    version: int = Field(..., ge=1, description="Version number to re-activate")


class ReleaseActionRequest(BaseModel):
    action: str = Field(..., description='hold / release / auto')

    @field_validator('action')
    @classmethod
    def _valid(cls, v):
        if v not in ('hold', 'release', 'auto'):
            raise ValueError('action must be hold/release/auto')
        return v


class TeachingFileRequest(BaseModel):
    """R-11: submit a completed case to the teaching file library."""
    exam_id: str = Field(..., description='Source exam (completed)')
    title: str = Field(..., min_length=1, description='Case title')
    diagnosis: str = Field('', description='Primary teaching diagnosis')
    body_part: str = Field('', description='Body part, for curriculum filters')
    difficulty: str = Field('medium', description='easy / medium / hard')

    @field_validator('difficulty')
    @classmethod
    def _valid_difficulty(cls, v):
        if v not in ('easy', 'medium', 'hard'):
            raise ValueError('difficulty must be easy/medium/hard')
        return v

    teaching_points: list[str] = Field(default_factory=list)
    differential_diagnosis: list[str] = Field(default_factory=list)
    annotations: object = Field(default=None,
                                description='Viewer annotation state')
    findings_text: str = Field('',
                               description='Optional findings narrative')
