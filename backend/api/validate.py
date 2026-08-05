"""Request body parsing with Pydantic v2 validation.
Usage: data = await parse_body(MySchema, request)
Returns validated model or raises _ValidationException caught by middleware."""
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from api.response import api_error


async def parse_body(model_class, request):
    try:
        data = await request.json()
        return model_class(**data)
    except ValidationError as e:
        errors = e.errors()
        details = [
            {
                'field': '.'.join(str(p) for p in err['loc']),
                'message': err['msg'],
                'type': err.get('type', ''),
            }
            for err in errors
        ]
        raise _ValidationException(details)


class _ValidationException(Exception):
    def __init__(self, details):
        self.details = details


def validation_exception_handler(request, exc):
    return api_error(
        'VALIDATION_ERROR',
        'Request validation failed',
        details=exc.details,
        status=422,
    )
