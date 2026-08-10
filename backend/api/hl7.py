import ipaddress

from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse

from api.rbac import requires_permission
from api.permissions import Permission
from config import config
from services.ingestion.hl7_server import default_handler
from log import get_logger

log = get_logger(__name__)

# HL7 HTTP bodies are single MLLP-framed messages; anything near this size
# is either a batch dump or an attack — refuse it before the parser runs.
_MAX_HL7_BODY_BYTES = 10 * 1024 * 1024


def _allowed_networks():
    """Parse hl7_mllp_allowed_ips (comma-separated CIDRs) once per request.

    Mirrors the MLLP listener's whitelist semantics (MllpServer) so the HTTP
    receiver can't bypass a network restriction configured for the listener.
    """
    networks = []
    for entry in [s.strip() for s in config.get('hl7_mllp_allowed_ips', '').split(',') if s.strip()]:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            log.warning('Invalid IP network in hl7_mllp_allowed_ips: %s', entry)
    return networks


class Hl7Receiver(HTTPEndpoint):
    @requires_permission(Permission.HL7_WRITE)
    async def post(self, request):
        networks = _allowed_networks()
        if networks:
            peer_ip = request.client.host if request.client else ''
            try:
                addr = ipaddress.ip_address(peer_ip)
            except ValueError:
                addr = None
            if addr is None or not any(addr in net for net in networks):
                log.warning('HL7 HTTP message rejected from %s (not in whitelist)', peer_ip)
                raise HTTPException(status_code=403, detail='Sender IP not allowed')

        body = await request.body()
        if len(body) > _MAX_HL7_BODY_BYTES:
            raise HTTPException(
                status_code=413, detail='HL7 message exceeds 10MB limit',
            )
        result = await default_handler(body)
        return PlainTextResponse(result.decode('utf-8') if isinstance(result, bytes) else result)
