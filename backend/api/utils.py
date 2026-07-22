from starlette.exceptions import HTTPException

from api.response import validation_error
from api.tokens import create_token as gen_token


def get_id(request):
    return int(request.path_params['id'])


def api_error(err, status_code=400):
    return validation_error(str(err))


def is_admin(request):
    if not request.user.admin:
        raise HTTPException(status_code=403)
