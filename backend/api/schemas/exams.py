from pydantic import BaseModel, Field, field_validator, model_validator


class CreateExamRequest(BaseModel):
    worklist_entry_id: str | None = Field(None, description="Adopt an existing worklist entry")
    patient_id: str | None = Field(None, description="Primary patient identifier (MRN)")
    patient_name: str = Field('', description="Patient name")
    patient_birth_date: str = Field('', description="Date of birth (YYYYMMDD)")
    patient_sex: str = Field('', description="Sex (M/F/O)")
    accession_number: str = Field('', description="Accession number")
    requested_procedure_desc: str = Field('', description="Requested procedure description")
    modality: str = Field('', description="DICOM modality (CT, MR, etc.)")
    station_ae_title: str = Field('', description="Station AE title")
    priority: str = Field('routine', description="routine/urgent/stat")
    protocol_name: str = Field('', description="Selected protocol name")
    referring_physician: str = Field('', description="Referring/ordering physician (ME-04)")

    @field_validator('priority')
    @classmethod
    def _valid_priority(cls, v):
        if v not in ('routine', 'urgent', 'stat'):
            raise ValueError('priority must be routine/urgent/stat')
        return v

    @model_validator(mode='after')
    def _at_least_one_identity(self):
        # Either adopt a worklist entry, or provide a patient id directly.
        if not self.worklist_entry_id and not self.patient_id:
            raise ValueError('provide worklist_entry_id or patient_id')
        return self


class IdentityConfirmRequest(BaseModel):
    confirmed: bool = Field(True, description="Patient identity verified")
    notes: str = Field('', description="Optional notes (e.g. mismatch observed)")


class StartProtocolRequest(BaseModel):
    protocol_name: str = Field('', description="Protocol to start")
    overridden_parameters: dict | None = Field(None, description="If overriding, new parameters")


class CreateAcquisitionRequest(BaseModel):
    series_number: int = Field(1, description="Series number within the exam")
    instance_uid: str = Field('', description="SOP instance UID of the acquired image")
    description: str = Field('', description="Series/sequence description")
    kvp: float = Field(0, description="Peak kilovoltage")
    mas: float = Field(0, description="Tube current-exposure time product")
    dlp: float = Field(0, description="Dose length product (mGy·cm)")
    ctdivol: float = Field(0, description="CTDI volume (mGy)")
    exposure_time: float = Field(0, description="Exposure time (ms)")


class AcquisitionDecisionRequest(BaseModel):
    reason: str = Field('', description="Reject reason or accept note")


class SafetyCheckRequest(BaseModel):
    checks: list[dict] = Field(..., description="List of {check_item, answer, notes}")


class CompleteExamRequest(BaseModel):
    dose_recorded: bool = Field(False, description="Dose data recorded")
    sequences_complete: bool = Field(False, description="All required sequences acquired")


class IncidentRequest(BaseModel):
    incident_type: str = Field(..., description="Type: patient_motion, equipment_malfunction, contrast_reaction, other")
    severity: str = Field('medium', description="low/medium/high/critical")
    description: str = Field(..., min_length=1, description="Free-text description")

    @field_validator('severity')
    @classmethod
    def _valid_severity(cls, v):
        if v not in ('low', 'medium', 'high', 'critical'):
            raise ValueError('severity must be low/medium/high/critical')
        return v


class OverrideRequest(BaseModel):
    justification: str = Field(..., min_length=1, description="Required override justification")
    overridden_parameters: dict = Field(default_factory=dict, description="Overridden protocol parameters")


class CriticalFlagRequest(BaseModel):
    """technologist review P1-1: flag an exam for immediate radiology read.

    severity mirrors the incident scale; series_id optionally points at the
    acquisition that triggered the flag; note is free-text justification.
    """
    severity: str = Field('critical', description="low/medium/high/critical")
    series_id: str | None = Field(None, description="Acquisition id that triggered the flag")
    note: str = Field(..., min_length=1, description="Why this is critical")

    @field_validator('severity')
    @classmethod
    def _valid_severity(cls, v):
        if v not in ('low', 'medium', 'high', 'critical'):
            raise ValueError('severity must be low/medium/high/critical')
        return v


class ClaimExamRequest(BaseModel):
    """T-02: claim (default) or release an exam. release=true returns the
    exam to the unassigned pool by clearing assigned_technologist."""
    release: bool = Field(False, description="Release back to the pool")
