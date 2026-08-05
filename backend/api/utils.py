from starlette.exceptions import HTTPException



def get_id(request):
    return int(request.path_params['id'])


def is_admin(request):
    if not request.user.admin:
        raise HTTPException(status_code=403)
