from typing import Optional

from pydantic import BaseModel, Field


class Hl7ConfigUpdate(BaseModel):
    mllp_port: Optional[int] = Field(None, description="HL7 MLLP listener port")
    allowed_ips: Optional[list[str]] = Field(None, description="List of IPs permitted to send HL7 messages")
