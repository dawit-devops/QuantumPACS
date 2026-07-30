from pydantic import BaseModel
from typing import Optional


class Hl7ConfigUpdate(BaseModel):
    mllp_port: Optional[int] = None
    allowed_ips: Optional[list[str]] = None
