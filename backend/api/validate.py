"""Request body parsing with Pydantic v2 validation.
Usage: data = await parse_body(MySchema, request)
Returns validated model or raises _ValidationException caught by middleware."""
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from api.response import validation_error


async def parse_body(model_class, request):
    try:
        data = await request.json()
        return model_class(**data)
    except ValidationError as e:
        errors = e.errors()
        message = '; '.join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in errors
        )
        raise _ValidationException(message)


class _ValidationException(Exception):
    def __init__(self, message):
        self.message = message


def validation_exception_handler(request, exc):
    return validation_error(exc.message)
