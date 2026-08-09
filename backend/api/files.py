import csv
import io
import os.path
from datetime import datetime, timezone
from zipfile import ZipFile
from uuid import uuid4

import numpy as np
from pydicom import dcmread
from PIL import Image
from starlette.endpoints import HTTPEndpoint
from starlette.responses import FileResponse, Response
from starlette.exceptions import HTTPException
from starlette.background import BackgroundTask

from api.tenant_middleware import effective_tenant
from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, not_found, no_content, api_error, paginated
from api.tokens import create_token as gen_token
from api.utils import get_id
from api.validate import parse_body
from api.schemas.files import FileUpdateRequest, ShareRequest
from api.notify import notify_role
from config import config as app_config
from db.conn import get_conn
from db.file_changes import FileChange
from db.files import Files
from db.replica import Replica
from db.replica_files import ReplicaFiles
from db.share_files import SharedFiles
from db.notifications import Notifications
from db.tenants import Tenants
from api.ws import broadcast_to_user
from dcm.file import parse_dcm
from es import es
from storage.storage import Storage
from utils import hash_file
from log import get_logger

log = get_logger(__name__)


_DICOM_MAGIC = b'\x00' * 4 + b'\x08\x00\x00\x00'


def _is_dicom(content: bytes) -> bool:
    return len(content) > 132 and content[128:132] == b'DICM'


_REQUIRED_DICOM_TAGS = ['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID']


async def _tenant_storage_used(request, tenant_info):
    """Current storage usage for the active tenant, in bytes.

    Prefers a live SUM over files.size on the tenant pool; falls back to the
    storage_used_bytes registry column when the pool is unavailable or the
    live query fails (e.g. tenant DB not yet migrated).
    """
    acquire = getattr(request.state, 'tenant_conn', None)
    if acquire is not None:
        try:
            async with acquire() as tconn:
                used = await tconn.fetchval(
                    'SELECT COALESCE(SUM(size), 0)::bigint FROM files'
                )
            return int(used or 0)
        except Exception:
            log.warning('Live tenant storage SUM failed; falling back to registry column', exc_info=True)
    return int(tenant_info.get('storage_used_bytes') or 0)


async def _persist_storage_used(conn, tenant_slug, used_bytes):
    """Record the tenant's new total storage usage in the tenants registry.

    Prefers Tenants.persist_storage_used; falls back to a direct UPDATE so the
    quota bookkeeping never blocks an upload.
    """
    try:
        persist = getattr(Tenants(conn), 'persist_storage_used', None)
        if persist is not None:
            await persist(tenant_slug, used_bytes)
            return
    except Exception:
        log.warning('persist_storage_used failed for tenant %s; using direct UPDATE', tenant_slug, exc_info=True)
    try:
        await conn.execute(
            'UPDATE tenants SET storage_used_bytes = $1, updated_at = now() WHERE slug = $2',
            used_bytes, tenant_slug,
        )
    except Exception:
        log.warning('Direct storage_used_bytes UPDATE failed for tenant %s', tenant_slug, exc_info=True)


async def _notify_quota_breach(conn, tenant_slug, quota_bytes, used_bytes):
    """Notify super admins when a tenant crosses 90% of its storage quota.

    Deliberately non-throwing: notifications must never break an upload.
    """
    try:
        pct = round(used_bytes / quota_bytes * 100, 1)
        await notify_role(
            conn,
            'super_admin',
            'storage.quota_breach',
            f'Tenant "{tenant_slug}" at {pct}% of storage quota',
            f'Storage usage reached {used_bytes} of {quota_bytes} bytes ({pct}%)',
            '/tenants',
        )
    except Exception:
        log.warning('Quota breach notification failed for tenant %s', tenant_slug, exc_info=True)


class Upload(HTTPEndpoint):
    @requires_permission(Permission.FILE_WRITE)
    async def post(self, request):
        form = await request.form()
        up = form['file']
        try:
            return await self._process_upload(request, up)
        finally:
            # Starlette spools the body to a temp file; close it explicitly so
            # it does not linger until GC (ResourceWarning in tests).
            await up.close()

    async def _process_upload(self, request, up):
        max_mb = int(app_config.get('max_upload_size_mb', '500'))
        max_bytes = max_mb * 1024 * 1024

        size_hint = request.headers.get('content-length')
        if size_hint and int(size_hint) > max_bytes:
            return api_error('FILE_TOO_LARGE', f'File exceeds {max_mb}MB limit', status=413)

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

        new_bytes = len(content)
        tenant_slug = getattr(request.state, 'tenant_slug', None)
        tenant_info = getattr(request.state, 'tenant', None) or {}
        quota_bytes = int(tenant_info.get('storage_quota_bytes') or 0)
        current_used = None

        # Quota enforcement only applies when a tenant is active (X-Tenant-ID
        # resolved by TenantMiddleware). Platform users have no tenant and are
        # not throttled.
        if tenant_slug:
            current_used = await _tenant_storage_used(request, tenant_info)
            if quota_bytes > 0 and current_used + new_bytes > quota_bytes:
                return api_error(
                    'QUOTA_EXCEEDED',
                    f'Upload of {new_bytes} bytes would exceed tenant storage quota of {quota_bytes} bytes '
                    f'(currently using {current_used} bytes). Free up space or contact an administrator.',
                    status=403,
                )

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
                # Byte count is authoritative — set after DICOM tags merge so a
                # tag named `size` can never shadow it.
                file_data['size'] = new_bytes
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

                if tenant_slug and current_used is not None:
                    new_total = current_used + new_bytes
                    await _persist_storage_used(conn, tenant_slug, new_total)
                    if quota_bytes > 0 and new_total / quota_bytes >= 0.9:
                        await _notify_quota_breach(conn, tenant_slug, quota_bytes, new_total)

                user_id = request.user.id
                patient_name = ds.get('patient_name', ds.get('patientname', 'Unknown'))
                await Notifications(conn).create(
                    user_id=user_id,
                    event_type='study.arrived',
                    title=f'Study arrived for {patient_name}',
                    body=f'File {filename} uploaded successfully',
                    link=f'/files/{filedata["id"]}',
                )
                await broadcast_to_user(
                    user_id,
                    {'type': 'notifications'},
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
                # Name by UID, not DB ids: the archive is reproducible and
                # self-describing for external DICOM tools (ME-07).
                meta = file.get('meta') or {}
                file['arcname'] = '/'.join([
                    meta.get('study_instance_uid') or str(file['study_id']),
                    meta.get('series_instance_uid') or str(file['series_id']),
                    meta.get('sop_instance_uid') or file['name'],
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

        results = await es.search(data)
        return ok(results)


def _outside_effective_tenant(request, user, file_tenant):
    """True when a file belongs to a tenant outside the request's current
    scope. The middleware has already authorized that scope (JWT claim,
    admin, or an R2-03 cross-tenant grant via X-Tenant-ID) — here we only
    refuse files belonging to a different tenant than the one this request
    is operating in. Files without a tenant stay accessible exactly as
    before."""
    if not file_tenant or user.admin:
        return False
    return effective_tenant(request) != file_tenant


async def get_file_by_id(request):
    file_id = int(request.path_params['id'])
    async with get_conn() as conn:
        file = await Files(conn).get_extra(file_id)
        if not file or file['deleted']:
            return None
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and _outside_effective_tenant(request, user, file.get('tenant')):
            return None
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
                if not file:
                    return not_found('File not found')
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

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and _outside_effective_tenant(request, user, file.get('tenant')):
            raise HTTPException(status_code=403)

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

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and _outside_effective_tenant(request, user, file.get('tenant')):
            raise HTTPException(status_code=403)

        tmp = await storage.fetch(file)
        try:
            ds = dcmread(tmp)
            payload = _render_preview(ds)
        except Exception as exc:
            log.warning('thumbnail render failed for file %s: %s', file_id, exc)
            return Response(status_code=404, content='Cannot generate thumbnail')

        return Response(content=payload, media_type='image/jpeg')


def _render_preview(ds) -> bytes:
    """Render a DICOM instance to a JPEG preview byte string.

    DICOM stores raw modality values (e.g. CT HU), so a usable preview
    needs the standard display pipeline — rescale slope/intercept, VOI
    window (or min/max stretch when no window is present), and photometric
    conversion. Without it, CT previews are near-black and color images
    (YBR_FULL) are corrupted.
    """
    arr = ds.pixel_array
    photometric = getattr(ds, 'PhotometricInterpretation', 'MONOCHROME2')

    if photometric == 'RGB':
        if getattr(ds, 'PlanarConfiguration', 0) == 1:
            arr = arr.transpose(1, 2, 0)
        img = Image.fromarray(arr)
    elif photometric in ('YBR_FULL', 'YBR_FULL_422', 'YBR_ICT', 'YBR_RCT'):
        from pydicom.pixel_data_handlers.util import convert_color_space
        try:
            rgb = convert_color_space(arr, 'YBR_FULL', 'RGB')
        except Exception:
            rgb = convert_color_space(arr, 'YBR_FULL_422', 'RGB') \
                if photometric == 'YBR_FULL_422' else None
        if rgb is not None:
            img = Image.fromarray(rgb)
        else:
            img = Image.fromarray(arr[..., 0])
    else:
        arr = arr.astype(np.float32)
        if arr.ndim > 2:
            # Multi-frame: preview the middle frame, not the first.
            arr = arr[arr.shape[0] // 2]
        slope = float(getattr(ds, 'RescaleSlope', 1) or 1)
        intercept = float(getattr(ds, 'RescaleIntercept', 0) or 0)
        arr = arr * slope + intercept
        wc = getattr(ds, 'WindowCenter', None)
        ww = getattr(ds, 'WindowWidth', None)
        if wc is not None and ww is not None:
            wc = float(wc[0] if isinstance(wc, (list, tuple)) else wc)
            ww = float(ww[0] if isinstance(ww, (list, tuple)) else ww)
            if ww > 0:
                lo, hi = wc - ww / 2, wc + ww / 2
                if hi > lo:
                    arr = np.clip((arr - lo) / (hi - lo), 0, 1)
        if photometric == 'MONOCHROME1':
            arr = 1.0 - arr
        amin, amax = float(np.min(arr)), float(np.max(arr))
        if amax > amin:
            arr = (arr - amin) / (amax - amin)
        img = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))

    if img.mode not in ('L', 'RGB'):
        img = img.convert('RGB')
    img.thumbnail((256, 256), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


class DownloadToken(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        token = gen_token(request.user.to_dict(), {'minutes': 1})
        return ok({'token': token})
