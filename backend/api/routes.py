import os
from starlette.routing import Router, Route, Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles

from starlette.responses import FileResponse, JSONResponse

from api.patient import PatientHandler
from api.files import (
    Upload, DownloadFiles, DownloadData, DownloadToken, FilesHandler, FileHandler,
    FileChangesHandler, ShareFilesHandler, ServeFile
)
from api.logs import LogsHandler
from api.replicas import ReplicasHandlers, ReplicaHandlers
from api.telemetry import health_endpoint, metrics_endpoint
from api.users import (
    Login, ChangePassword, UsersHandler, UsersDeactivate, UsersNewPassword,
)
from api.ws import WSToken, WebsocketHandler
from config import is_docker


DIR = os.path.dirname(os.path.abspath(__file__))


async def docs_page(request):
    return FileResponse(os.path.join(DIR, '..', 'static', 'docs.html'), media_type='text/html')


async def openapi_spec(request):
    return FileResponse(os.path.join(DIR, '..', 'static', 'openapi.json'), media_type='application/json')


routes = [
    Route('/health', endpoint=health_endpoint),
    Route('/metrics', endpoint=metrics_endpoint),
    Route('/docs', endpoint=docs_page),
    Route('/docs/openapi.json', endpoint=openapi_spec),
    Route('/replicas', endpoint=ReplicasHandlers),
    Route('/replicas/{id}', endpoint=ReplicaHandlers),
    Route('/login', endpoint=Login),
    Route('/change_password', endpoint=ChangePassword),
    Route('/users', endpoint=UsersHandler),
    Route('/users/deactivate', endpoint=UsersDeactivate),
    Route('/users/new_password', endpoint=UsersNewPassword),
    Route('/patients/{id}', endpoint=PatientHandler),
    Route('/files/upload', endpoint=Upload),
    Route('/files/download_token', endpoint=DownloadToken),
    Route('/files/download.zip', endpoint=DownloadFiles),
    Route('/files/download.csv', endpoint=DownloadData),
    Route('/files', endpoint=FilesHandler),
    Route('/files/{id}', endpoint=FileHandler),
    Route('/files/{id}/changes', endpoint=FileChangesHandler),
    Route('/files/{id}/share', endpoint=ShareFilesHandler),
    Route('/files/{id}/data', endpoint=ServeFile),
    Route('/logs', endpoint=LogsHandler),
    Route('/ws_token', endpoint=WSToken),
    WebSocketRoute('/ws', endpoint=WebsocketHandler)
]
routes = [
    Mount('/api', app=Router(routes)),
]
if is_docker:
    routes.append(Mount('/', app=StaticFiles(directory='static'), name="static"))
