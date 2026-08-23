from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SubmitConsentRequest(BaseModel):
    """K-03 kiosk digital consent submission.

    accepted=True requires a signature PNG; a decline must carry a reason
    (spec: "I decline" button with mandatory reason field, still allows
    check-in).
    """
    accepted: bool = Field(description="Patient accepted the imaging consent")
    signature_png: str = Field('', max_length=2_000_000,
                               description="Signature as base64 PNG data URI")
    decline_reason: str = Field('', max_length=500,
                                description="Mandatory reason when declined")

    @field_validator('signature_png')
    @classmethod
    def _signature_required_when_accepted(cls, v, info):
        accepted = info.data.get('accepted')
        if accepted and not v:
            raise ValueError('signature_png is required when consent is accepted')
        return v

    @field_validator('decline_reason')
    @classmethod
    def _reason_required_when_declined(cls, v, info):
        accepted = info.data.get('accepted')
        if accepted is False and not v.strip():
            raise ValueError('decline_reason is required when consent is declined')
        return v


class SubmitPaymentRequest(BaseModel):
    """K-04 kiosk co-pay capture — mirrors BillingPaymentRequest minus the
    operator (the kiosk token is the actor)."""
    method: Literal['cash', 'card', 'check'] = Field(
        description="Payment method")
    amount: float = Field(..., gt=0,
                          description="Co-pay amount (must be positive)")
    idempotency_key: str = Field(
        ..., min_length=1,
        description="Client-supplied key for duplicate payment detection")
    processor_token: str = Field(
        '', description="Card processor token — never a raw PAN")