"""Pydantic v2 schemas for communications (CS7/CC-04)."""

from pydantic import BaseModel, Field, field_validator

DIRECTIONS = ('inbound', 'outbound')
COMMS_CHANNELS = ('phone', 'email', 'sms', 'fax', 'letter', 'portal')


class CommunicationRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=128)
    direction: str = Field(..., max_length=16)
    channel: str = Field('phone', max_length=16)
    category: str = Field('', max_length=64)
    summary: str = Field(..., min_length=1, max_length=4000)
    related_order_id: str = Field('', max_length=128)

    @field_validator('direction')
    @classmethod
    def _valid_direction(cls, v):
        if v not in DIRECTIONS:
            raise ValueError(f'direction must be one of {DIRECTIONS}')
        return v

    @field_validator('channel')
    @classmethod
    def _valid_channel(cls, v):
        if v not in COMMS_CHANNELS:
            raise ValueError(f'channel must be one of {COMMS_CHANNELS}')
        return v
