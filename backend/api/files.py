import csv
import io
import os.path
from zipfile import ZipFile
from uuid import uuid4

from pydicom import dcmread
from PIL import Image
from starlette.endpoints import HTTPEndpoint
from starlette.responses import FileResponse, Response
from starlette.exceptions import HTTPException
from starlette.background import BackgroundTask

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, not_found, no_content, api_error, paginated
from api.tokens import create_token as gen_token
from api.utils import get_id
from api.validate import parse_body
from api.schemas.files import FileUpdateRequest, ShareRequest
from db.conn import get_conn
from db.file_changes import FileChange
from db.files import Files
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.share_files import SharedFiles
from dcm.file import parse_dcm
from es import es
from storage.storage import Storage
from utils import hash_file


class Upload(HTTPEndpoint):
    @requires_permission(Permission.FILE_WRITE)
    async def post(self, request):
        form = await request.form()
        filename = form['file'].filename
        file = form['file'].file

        async with get_conn() as conn:
            async with conn.transaction():
                master = await Replica(conn).master()
                if not master:
                    return api_error('NO_MASTER', 'No master replica set')

                ds = parse_dcm(file)
                hsh = hash_file(file)

                file_data = {
                    'name': os.path.basename(filename),
                    'master': master['id'],
                    'hash': hsh,
                }
                file_data.update(ds)
                filedata = await Files(conn).insert_or_select(file_data)

                storage = await Storage.get(master)
                ret = await storage.copy(file, filedata)

                await ReplicaFiles(conn).add(
                    master['id'],
                    [{'id': filedata['id'], **ret}],
                )
        return no_content()


def zip_files(files, zipname):
    with ZipFile(zipname, 'w') as myzip:
        for f in files:
            if isinstance(f['tmp'], str):
                myzip.write(f['tmp'], arcname=f['arcname'])
            else:
                myzip.writestr(f['arcname'], data=f['tmp'].read())


class DownloadFiles(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        data = [int(i) for i in request.query_params['ids'].split(',')]
        files = []
        async with get_conn() as conn:
            master = await Replica(conn).master()
            storage = await Storage.get(master)

            for d in data:
                file = await ReplicaFiles(conn).get_file_from_replica(master['id'], d)
                tmp = await storage.fetch(file)
                file['tmp'] = tmp
                file['arcname'] = '_'.join([
                    str(file['patient_id']),
                    str(file['study_id']) or 'empty',
                    str(file['series_number']) or 'empty',
                    file['name'],
                ])
                files.append(file)

        tmp = uuid4()
        zipname = f'/tmp/{tmp}.zip'
        await BackgroundTask(zip_files, files, zipname)()
        return FileResponse(zipname)


class DownloadData(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        data = [int(i) for i in request.query_params['ids'].split(',')]
        columns = set([])
        rows = []
        async with get_conn() as conn:
            master = await Replica(conn).master()

            for d in data:
                file = await ReplicaFiles(conn).get_file_from_replica(master['id'], d)
                columns.update(file['meta'].keys())
                rows.append(file['meta'])

        columns = list(columns)
        columns.sort()
        tmp = uuid4()
        tmp_csv = f'/tmp/{tmp}.csv'
        with open(tmp_csv, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(columns)

            for r in rows:
                row = [r.get(c, '') for c in columns]
                csvwriter.writerow(row)

        return FileResponse(tmp_csv)


class FilesHandler(HTTPEndpoint):
    async def get(self, request):
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        search = request.query_params.get('q')

        async with get_conn() as conn:
            data, total = await Files(conn).get_paginated(
                page=page, per_page=per_page, search=search,
            )

        return paginated(data, total=total, page=page, per_page=per_page, request=request)

    async def post(self, request):
        data = await request.json()

        async with get_conn() as conn:
            data = await es.search(data)
            return ok(data)


async def get_file_by_id(request):
    file_id = int(request.path_params['id'])
    async with get_conn() as conn:
        file = await Files(conn).get_extra(file_id)
        if not file or file['deleted']:
            raise HTTPException(status_code=404)
        return file


class FileHandler(HTTPEndpoint):
    async def get(self, request):
        data = await get_file_by_id(request)
        if not data:
            return not_found()
        async with get_conn() as conn:
            await FileChange(conn).add_change(
                data['id'], 'read', by_user=request.user.id,
            )
        return ok(data)

    async def post(self, request):
        file_id = get_id(request)
        body = await parse_body(FileUpdateRequest, request)
        if body.tools_state:
            async with get_conn() as conn:
                await Files(conn).update_tools_state(
                    file_id,
                    request.user.id,
                    body.tools_state,
                )
        if body.tag:
            async with get_conn() as conn:
                await Files(conn).update_tag(
                    file_id,
                    request.user.id,
                    body.tag,
                )
        return ok(body.model_dump(exclude_none=True))

    @requires_permission(Permission.FILE_DELETE)
    async def delete(self, request):
        async with get_conn() as conn:
            async with conn.transaction():
                master = await Replica(conn).master()
                if not master:
                    return api_error('NO_MASTER', 'No master replica set')

                file = await get_file_by_id(request)
                storage = await Storage.get(master)
                await storage.delete(file)

                await Files(conn).delete(file['id'], master['id'])
        return no_content()


class FileChangesHandler(HTTPEndpoint):
    async def get(self, request):
        file_id = get_id(request)
        async with get_conn() as conn:
            data = await FileChange(conn).for_file(file_id)

        return ok({'data': data})


class ServeFile(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        file_id = get_id(request)
        if not file_id:
            raise HTTPException(status_code=404)

        async with get_conn() as conn:
            master = await Replica(conn).master()
            file = await ReplicaFiles(conn).get_file_from_replica(master['id'], file_id)
            storage = await Storage.get(master)

        if not file:
            raise HTTPException(status_code=404)

        async with get_conn() as conn:
            await FileChange(conn).add_change(
                file_id, 'download', by_user=request.user.id,
            )
        return await storage.serve(file)


class ShareFilesHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_WRITE)
    async def post(self, request):
        file_id = get_id(request)
        body = await parse_body(ShareRequest, request)

        async with get_conn() as conn:
            key = await SharedFiles(conn).share(file_id, body.duration)
        return ok({'key': key})


class ServeThumbnail(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        file_id = get_id(request)
        if not file_id:
            raise HTTPException(status_code=404)

        async with get_conn() as conn:
            master = await Replica(conn).master()
            file = await ReplicaFiles(conn).get_file_from_replica(master['id'], file_id)
            storage = await Storage.get(master)

        if not file:
            raise HTTPException(status_code=404)

        tmp = await storage.fetch(file)
        try:
            ds = dcmread(tmp)
            pixel_array = ds.pixel_array
            if pixel_array.ndim > 2:
                pixel_array = pixel_array[0]
            img = Image.fromarray(pixel_array)
            img = img.convert('L')
            img.thumbnail((256, 256), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85)
            payload = buf.getvalue()
        except Exception:
            pixel_array = None

        if pixel_array is None:
            return Response(status_code=404, content='Cannot generate thumbnail')

        return Response(content=payload, media_type='image/jpeg')


class DownloadToken(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        token = gen_token(request.user.to_dict(), {'minutes': 1})
        return ok({'token': token})
