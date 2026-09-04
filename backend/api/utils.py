from starlette.exceptions import HTTPException



def get_id(request):
    """Numeric path id → int. A non-numeric id (e.g. a patient MRN routed to
    a numeric-id endpoint) is a client error, not a server fault: raise 404
    so the caller sees a normal miss instead of a 500 traceback."""
    raw = request.path_params['id']
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404)


def is_admin(request):
    if not request.user.admin:
        raise HTTPException(status_code=403)
