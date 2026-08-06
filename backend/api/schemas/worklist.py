from datetime import date, time

from pydantic import BaseModel, Field


class CreateWorklistRequest(BaseModel):
    patient_id: str = Field(description="Primary patient identifier (MRN)")
    patient_name: str = Field('', description="Patient name in DICOM format (^ delimited)")
    patient_birth_date: str = Field('', description="Patient date of birth (YYYYMMDD)")
    patient_sex: str = Field('', description="Patient sex (M/F/O)")
    accession_number: str = Field('', description="Accession number for the scheduled procedure")
    requested_procedure_id: str = Field('', description="Identifier for the requested procedure")
    requested_procedure_desc: str = Field('', description="Description of the requested procedure")
    scheduled_procedure_step_id: str = Field('', description="Identifier for the scheduled procedure step")
    protocol_name: str = Field('', description="Protocol name for the scheduled step")
    requesting_physician: str = Field('', description="Requesting physician name (^ delimited)")
    scheduled_date: date | None = Field(None, description="Scheduled procedure date")
    scheduled_time: time | None = Field(None, description="Scheduled procedure time")
    modality: str = Field('', description="DICOM modality (CT, MR, etc.)")
    station_ae_title: str = Field('', description="DICOM AE title of the scheduled station")


class UpdateWorklistRequest(BaseModel):
    patient_name: str | None = Field(None, description="Updated patient name")
    patient_birth_date: str | None = Field(None, description="Updated date of birth")
    patient_sex: str | None = Field(None, description="Updated sex")
    accession_number: str | None = Field(None, description="Updated accession number")
    requested_procedure_id: str | None = Field(None, description="Updated procedure ID")
    requested_procedure_desc: str | None = Field(None, description="Updated procedure description")
    scheduled_procedure_step_id: str | None = Field(None, description="Updated procedure step ID")
    protocol_name: str | None = Field(None, description="Updated protocol name")
    requesting_physician: str | None = Field(None, description="Updated requesting physician")
    scheduled_date: date | None = Field(None, description="Updated scheduled date")
    scheduled_time: time | None = Field(None, description="Updated scheduled time")
    modality: str | None = Field(None, description="Updated modality")
    station_ae_title: str | None = Field(None, description="Updated station AE title")
    status: str | None = Field(None, description="Entry status (scheduled/performed/cancelled)")
