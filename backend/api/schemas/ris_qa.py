"""Schemas for QA-09 Protocol Registry and QA-11 Corrective Actions."""

from pydantic import BaseModel
from typing import Optional


class CreateProtocolRequest(BaseModel):
    name: str
    modality: str = ''
    content: str = ''
    is_default: bool = False


class UpdateProtocolRequest(BaseModel):
    name: Optional[str] = None
    modality: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None


class CreateCorrectiveActionRequest(BaseModel):
    title: str
    description: str = ''
    assignee_id: str = ''
    incident_id: str = ''
    priority: str = 'medium'
    due_date: Optional[str] = None  # ISO timestamp string


class UpdateCorrectiveActionRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    incident_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
