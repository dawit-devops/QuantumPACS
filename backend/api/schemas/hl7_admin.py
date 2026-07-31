from pydantic import BaseModel


class Hl7ConfigUpdate(BaseModel):
    mllp_port: int | None = None
    allowed_ips: list[str] | None = None
