"""Pydantic v2 schemas for reminders (R2-02).

Channel literals mirror the ris_message_log / ris_reminder_config CHECK.
"""
from pydantic import BaseModel, Field, field_validator

REMINDER_CHANNELS = ('sms', 'email', 'phone')


class SendReminderRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    recipient: str = Field(..., min_length=1, max_length=256)
    channel: str = Field('email', max_length=10)
    subject: str = Field('', max_length=256)
    body: str = Field('', max_length=2000)

    @field_validator('channel')
    @classmethod
    def _valid_channel(cls, v):
        if v not in REMINDER_CHANNELS:
            raise ValueError(f'channel must be one of {REMINDER_CHANNELS}')
        return v


class ReminderConfigRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    channel: str = Field('email', max_length=10)
    template: str = Field('', max_length=2000)
    lead_time_hours: int = Field(24, ge=1, le=24 * 30)
    active: bool = True

    @field_validator('channel')
    @classmethod
    def _valid_channel(cls, v):
        if v not in REMINDER_CHANNELS:
            raise ValueError(f'channel must be one of {REMINDER_CHANNELS}')
        return v
