import csv
import io
import os.path
from datetime import datetime, timezone
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
from config import config as app_config
from db.conn import get_conn
from db.file_changes import FileChange
from db.files import Files
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.share_files import SharedFiles
from db.notifications import Notifications
from dcm.file import parse_dcm
from es import es
from storage.storage import Storage
from utils import hash_file


_DICOM_MAGIC = b'\x00' * 4 + b'\x08\x00\x00\x00'


def _is_dicom(content: bytes) -> bool:
    return len(content) > 132 and content[128:132] == b'DICM'


_REQUIRED_DICOM_TAGS = ['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID']


class Upload(HTTPEndpoint):
    @requires_permission(Permission.FILE_WRITE)
    async def post(self, request):
        max_mb = int(app_config.get('max_upload_size_mb', '500'))
        max_bytes = max_mb * 1024 * 1024

        size_hint = request.headers.get('content-length')
        if size_hint and int(size_hint) > max_bytes:
            return api_error('FILE_TOO_LARGE', f'File exceeds {max_mb}MB limit', status=413)

        form = await request.form()
        up = form['file']
        filename = up.filename
        file = up.file

        header = file.read(256)
        if not header or not _is_dicom(header):
            return api_error('INVALID_FILE', 'Not a valid DICOM file', status=400)

        remaining = file.read()
        content = header + remaining
        if len(content) > max_bytes:
            return api_error('FILE_TOO_LARGE', f'File exceeds {max_mb}MB limit', status=413)

        import io
        buf = io.BytesIO(content)

        try:
            ds = parse_dcm(buf)
        except Exception as e:
            return api_error('PARSE_ERROR', f'Could not parse DICOM: {e}', status=400)

        missing = [t for t in _REQUIRED_DICOM_TAGS if not ds.get(t.lower())]
        if missing:
            return api_error('INVALID_DICOM', f'Missing required DICOM tags: {", ".join(missing)}', status=400)

        hsh = hash_file(buf)

        async with get_conn() as conn:
            async with conn.transaction():
                master = await Replica(conn).master()
                if not master:
                    return api_error('NO_MASTER', 'No master replica set')

                existing = await Files(conn).find_by_hash(hsh)
                if existing:
                    return ok({'id': existing['id'], 'duplicate': True})

                file_data = {
                    'name': os.path.basename(filename),
                    'master': master['id'],
                    'hash': hsh,
                }
                file_data.update(ds)
                filedata = await Files(conn).insert_or_select(file_data)

                buf.seek(0)
                storage = await Storage.get(master)
                try:
                    ret = await storage.copy(buf, filedata)
                except Exception:
                    return api_error('STORAGE_ERROR', 'Failed to store file', status=500)

                await ReplicaFiles(conn).add(
                    master['id'],
                    [{'id': filedata['id'], **ret}],
                )
                user_id = request.user.id
                patient_name = ds.get('patient_name', ds.get('patientname', 'Unknown'))
                await Notifications(conn).create(
                    user_id=user_id,
                    event_type='study.arrived',
                    title=f'Study arrived for {patient_name}',
                    body=f'File {filename} uploaded successfully',
                    link=f'/files/{filedata["id"]}',
                )
        return ok({'id': filedata['id'], 'duplicate': False})


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
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        search = request.query_params.get('q')

        async with get_conn() as conn:
            data, total = await Files(conn).get_paginated(
                page=page, per_page=per_page, search=search,
            )

        return paginated(data, total=total, page=page, per_page=per_page, request=request)

    @requires_permission(Permission.FILE_READ)
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
    @requires_permission(Permission.FILE_READ)
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


class ShareFilesListHandler(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        file_id = get_id(request)
        async with get_conn() as conn:
            rows = await SharedFiles(conn).list_for_file(file_id)
        now = datetime.now(timezone.utc)
        result = []
        for r in rows:
            expires = r['expires']
            result.append({
                'id': r['id'],
                'created': str(r['created']),
                'expires': str(expires),
                'hash': r['hash'][:12] + '…',
                'active': expires > now,
            })
        return ok(result)

    @requires_permission(Permission.FILE_WRITE)
    async def delete(self, request):
        file_id = get_id(request)
        share_id = int(request.path_params['share_id'])
        async with get_conn() as conn:
            await SharedFiles(conn).revoke(share_id, file_id)
        return ok({'message': 'Share link revoked'})


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
