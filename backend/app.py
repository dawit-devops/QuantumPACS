import time

from starlette.applications import Starlette
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException
from starlette.routing import Route

import lifecycle
from api.auth import TokenAuth
from api.routes import routes
from api.response import server_error
from config import is_docker
from log import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)

app = Starlette(routes=routes + [
    Route('/api/health', endpoint=lambda r: JSONResponse({'status': 'ok'})),
])
app.add_middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error)


def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'OPTIONS,GET,POST,DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Origin,Accept,X-Auth-Pacs,Content-Type,X-Requested-With'


@app.middleware("http")
async def custom_middleware(request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start

    if response.status_code == 405:
        response.status_code = 200

    if is_docker and not request.url.path.startswith('/api') and response.status_code == 404:
        response = FileResponse('./static/index.html')

    if response.status_code >= 500:
        log.error('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)
    elif response.status_code >= 400:
        log.warning('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)
    else:
        log.info('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)

    add_cors(response)
    return response


@app.exception_handler(HTTPException)
async def http_exception(request, exc):
    resp = server_error(exc.detail if hasattr(exc, 'detail') else '', status_code=exc.status_code)
    add_cors(resp)
    return resp


@app.on_event('startup')
async def setup():
    await lifecycle.setup()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='localhost', port=8080)
