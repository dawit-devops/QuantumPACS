from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateEquipmentRequest(BaseModel):
    identifier: str = Field(min_length=1, description="Equipment identifier (unique registry code)")
    modality: str = Field('', description="Imaging modality (CT, MR, etc.)")
    manufacturer: str = Field('', description="Manufacturer name")
    model: str = Field('', description="Model name")
    serial_number: str = Field('', description="Serial number")
    location: str = Field('', description="Physical location in the facility")
    acquisition_date: date | None = Field(None, description="Date the equipment was acquired")
    operational_status: Literal['operational', 'maintenance', 'down', 'retired'] = Field(
        'operational', description="Operational status",
    )
    warranty_end_date: date | None = Field(None, description="Warranty expiration date")


class UpdateEquipmentRequest(BaseModel):
    identifier: str | None = Field(None, min_length=1, description="Updated equipment identifier")
    modality: str | None = Field(None, description="Updated modality")
    manufacturer: str | None = Field(None, description="Updated manufacturer")
    model: str | None = Field(None, description="Updated model")
    serial_number: str | None = Field(None, description="Updated serial number")
    location: str | None = Field(None, description="Updated location")
    acquisition_date: date | None = Field(None, description="Updated acquisition date")
    operational_status: Literal['operational', 'maintenance', 'down', 'retired'] | None = Field(
        None, description="Updated operational status",
    )
    warranty_end_date: date | None = Field(None, description="Updated warranty end date")


class CreateScheduleRequest(BaseModel):
    schedule_type: Literal['pm', 'qc'] = Field('pm', description="Type of schedule (preventive maintenance or QC)")
    title: str = Field('', description="Human-readable schedule title")
    frequency_days: int = Field(90, description="Interval between completions, in days")
    next_due_date: date | None = Field(None, description="Next due date (defaults to today + frequency_days)")


class ScheduleActionRequest(BaseModel):
    action: Literal['complete'] = Field(description="Action to apply to the schedule")


class CreateQcRecordRequest(BaseModel):
    test_type: str = Field(description="Type of QC test performed (e.g. kV accuracy)")
    pass_fail: Literal['pass', 'fail'] = Field(description="QC test outcome")
    measured_values: dict | None = Field(None, description="Raw measured values captured during the test")
    schedule_id: str | None = Field(None, description="Maintenance schedule this QC test fulfills, if any")


class CreateDowntimeRequest(BaseModel):
    cause_category: str = Field(description="Cause of the downtime (should come from a picklist)")
    impact: str = Field('', description="Operational impact description")
    start_at: datetime | None = Field(None, description="Downtime start (defaults to now)")


class UpdateDowntimeRequest(BaseModel):
    end_at: datetime | None = Field(None, description="Downtime end (defaults to now)")
    resolution: str = Field('', description="Resolution notes")
    cause_category: str | None = Field(None, description="Updated cause category")
    impact: str | None = Field(None, description="Updated impact description")


class CreateWorkOrderRequest(BaseModel):
    equipment_id: str = Field(description="Equipment the work order applies to")
    description: str = Field(description="Description of the work required")


class UpdateWorkOrderRequest(BaseModel):
    status: Literal['open', 'in_progress', 'on_hold', 'resolved'] | None = Field(
        None, description="Work order status (lifecycle: open → in_progress → on_hold → resolved)",
    )
    assigned_to: str | None = Field(None, description="Assignee")
    notes: str | None = Field(None, description="Work notes")


class CreateContractRequest(BaseModel):
    vendor_name: str = Field('', description="Vendor name")
    coverage_terms: str = Field('', description="Coverage terms summary")
    warranty_end_date: date | None = Field(None, description="Warranty end date under this contract")
    response_sla_p1_minutes: int = Field(15, description="Priority 1 response SLA in minutes")
    response_sla_p2_minutes: int = Field(240, description="Priority 2 response SLA in minutes")


class UpdateContractRequest(BaseModel):
    vendor_name: str | None = Field(None, description="Updated vendor name")
    coverage_terms: str | None = Field(None, description="Updated coverage terms")
    warranty_end_date: date | None = Field(None, description="Updated warranty end date")
    response_sla_p1_minutes: int | None = Field(None, description="Updated P1 response SLA in minutes")
    response_sla_p2_minutes: int | None = Field(None, description="Updated P2 response SLA in minutes")


class CreatePartRequest(BaseModel):
    part_name: str = Field(description="Name of the spare part")
    stock_level: int = Field(0, description="Current stock level")
    low_stock_threshold: int = Field(5, description="Level below which the part is flagged low stock")
    unit: str = Field('unit', description="Stock unit of measure")


class UpdatePartRequest(BaseModel):
    stock_level: int | None = Field(None, description="Updated stock level")
    low_stock_threshold: int | None = Field(None, description="Updated low stock threshold")
    unit: str | None = Field(None, description="Updated unit of measure")
