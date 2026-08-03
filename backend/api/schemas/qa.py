from pydantic import BaseModel, Field, field_validator


class SubmitQAScoreRequest(BaseModel):
    exam_id: str = Field(..., description="Exam being reviewed")
    protocol_id: str | None = Field(None, description="Protocol registry id")
    pass_fail: str = Field('pass', description="pass/fail/skipped")
    discrepancy_level: str = Field('none', description="none/minor/major/critical")
    dose_dlp: float = Field(0, ge=0, description="Dose length product (mGy·cm)")
    dose_ctdivol: float = Field(0, ge=0, description="CTDI volume (mGy)")
    dose_kvp: float = Field(0, ge=0, description="Peak kilovoltage")
    dose_mas: float = Field(0, ge=0, description="Tube current-time product")
    sequence_compliance: dict = Field(
        default_factory=dict, description="Map of sequence name -> bool",
    )
    comments: str = Field('', max_length=500, description="QA comments")

    @field_validator('pass_fail')
    @classmethod
    def _valid_pass_fail(cls, v):
        if v not in ('pass', 'fail', 'skipped'):
            raise ValueError('pass_fail must be pass/fail/skipped')
        return v

    @field_validator('discrepancy_level')
    @classmethod
    def _valid_discrepancy(cls, v):
        if v not in ('none', 'minor', 'major', 'critical'):
            raise ValueError('discrepancy_level must be none/minor/major/critical')
        return v


class SaveProtocolRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Protocol name")
    protocol_code: str = Field('', max_length=40, description="Unique alphanumeric code")
    modality: str = Field(..., description="CT/MR/US/DX/MG/FL/PET")
    body_part: str = Field('', max_length=80, description="Body part")
    sequences: list = Field(
        default_factory=list,
        description="Required sequences: [{name, phase, contrast}]",
    )
    parameters: dict = Field(default_factory=dict, description="Technique parameters")
    acr_benchmark_dlp: float | None = Field(None, ge=0, description="ACR DLP benchmark")
    acr_benchmark_ctdivol: float | None = Field(None, ge=0, description="ACR CTDIvol benchmark")
    acr_benchmark_min_snr: float | None = Field(None, ge=0, description="ACR minimum SNR")
    is_default: bool = Field(False, description="Default for modality")

    @field_validator('protocol_code')
    @classmethod
    def _valid_code(cls, v):
        if v and not v.replace('_', '').isalnum():
            raise ValueError('protocol_code must be alphanumeric')
        return v.upper()


class UpdateProtocolRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    protocol_code: str | None = Field(None, max_length=40)
    modality: str | None = Field(None)
    body_part: str | None = Field(None, max_length=80)
    sequences: list | None = Field(None)
    parameters: dict | None = Field(None)
    acr_benchmark_dlp: float | None = Field(None, ge=0)
    acr_benchmark_ctdivol: float | None = Field(None, ge=0)
    acr_benchmark_min_snr: float | None = Field(None, ge=0)
    is_default: bool | None = Field(None)

    @field_validator('protocol_code')
    @classmethod
    def _valid_code(cls, v):
        if v and not v.replace('_', '').isalnum():
            raise ValueError('protocol_code must be alphanumeric')
        return v.upper() if v else v


class LogQAIncidentRequest(BaseModel):
    exam_id: str | None = Field(None, description="Optional linked exam")
    study_uid: str = Field('', description="Study UID (if not exam-linked)")
    repeat_study_uid: str = Field('', description="Optional repeat study UID")
    incident_type: str = Field(..., description="Type of incident")
    severity: str = Field('medium', description="low/medium/high/critical")
    description: str = Field(..., max_length=500, description="Incident description")

    @field_validator('incident_type')
    @classmethod
    def _valid_type(cls, v):
        allowed = {
            'positioning', 'artifact', 'protocol_deviation', 'patient_motion',
            'equipment_malfunction', 'contrast_extravasation',
        }
        if v not in allowed:
            raise ValueError(f'incident_type must be one of {sorted(allowed)}')
        return v

    @field_validator('severity')
    @classmethod
    def _valid_severity(cls, v):
        if v not in ('low', 'medium', 'high', 'critical'):
            raise ValueError('severity must be low/medium/high/critical')
        return v


class CreateCorrectiveActionRequest(BaseModel):
    source: str = Field('R05_self', description="R03/R05_self/R06")
    issue: str = Field(..., min_length=1, max_length=500, description="Issue description")
    study_uids: list = Field(default_factory=list, description="Affected study UIDs")
    assigned_to: str = Field('', description="Assignee user id")

    @field_validator('source')
    @classmethod
    def _valid_source(cls, v):
        if v not in ('R03', 'R05_self', 'R06'):
            raise ValueError('source must be R03/R05_self/R06')
        return v


class ResolveCorrectiveActionRequest(BaseModel):
    findings: str = Field(..., min_length=1, max_length=500, description="Review findings")
    actions_taken: str = Field(..., min_length=1, max_length=500, description="Actions taken")


class ResolveIncidentRequest(BaseModel):
    notes: str = Field(..., min_length=1, max_length=500, description="Resolution notes")
