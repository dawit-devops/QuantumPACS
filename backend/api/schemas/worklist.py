from datetime import date, time

from pydantic import BaseModel


class CreateWorklistRequest(BaseModel):
    patient_id: str
    patient_name: str = ''
    patient_birth_date: str = ''
    patient_sex: str = ''
    accession_number: str = ''
    requested_procedure_id: str = ''
    requested_procedure_desc: str = ''
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    modality: str = ''
    station_ae_title: str = ''


class UpdateWorklistRequest(BaseModel):
    patient_name: str | None = None
    patient_birth_date: str | None = None
    patient_sex: str | None = None
    accession_number: str | None = None
    requested_procedure_id: str | None = None
    requested_procedure_desc: str | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    modality: str | None = None
    station_ae_title: str | None = None
