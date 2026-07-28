from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse

from services.ingestion.hl7_server import default_handler
from log import get_logger

log = get_logger(__name__)


class Hl7Receiver(HTTPEndpoint):
    async def post(self, request):
        body = await request.body()
        result = await default_handler(body)
        return PlainTextResponse(result.decode('utf-8') if isinstance(result, bytes) else result)
