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