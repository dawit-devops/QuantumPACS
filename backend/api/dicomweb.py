"""DICOMweb REST API endpoints — implements QIDO-RS (search), WADO-RS (retrieve), and STOW-RS
(store) conforming to the DICOMweb standard. Provides JSON and bulk-data access to studies,
series, and instances stored in the QuantumPACS backend."""
import json
from io import BytesIO

import aiofiles
from pydicom import dcmread
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response, StreamingResponse

from api.rbac import requires_permission
from api.permissions import Permission
from db.conn import get_conn
from db.replica import Replica
from dcm.dicom_json import row_to_study_json
from dcm.store import store_instance
from storage.storage import Storage

VALID_MODALITIES = frozenset({
    'CR', 'CT', 'MR', 'US', 'OT', 'BI', 'CD', 'DD', 'DG', 'ES', 'LS',
    'PT', 'RG', 'ST', 'TG', 'XA', 'XC', 'AS', 'DS', 'CF', 'DF', 'DM',
    'EC', 'FA', 'CS', 'LP', 'MA', 'MS', 'NM', 'DX', 'GM', 'HD',
    'IO', 'IX', 'PX', 'RF', 'SM', 'SR', 'VA', 'MG', 'EPS', 'OP',
    'OAM', 'OCT', 'OPT', 'OPV', 'OSS', 'POS', 'IVOCT', 'LEN',
})


def validate_modality(modality: str) -> bool:
    return modality in VALID_MODALITIES


class DicomJsonResponse(Response):
    media_type = 'application/dicom+json'


class _Pagination:
    def __init__(self, params):
        limit = params.get('limit')
        offset = params.get('offset')
        self.limit = int(limit) if limit and limit.isdigit() else 100
        self.offset = int(offset) if offset and offset.isdigit() else 0


def _apply_includefield(rows, params):
    """Filter DICOMweb rows to the tags requested via `includefield`.

    Per PS3.18 QIDO-RS, `includefield` is a comma-separated list of DICOM
    tags (or `all`). An empty/absent value returns the full default field
    set. Unknown tags are ignored.
    """
    raw = params.get('includefield') or params.get('includefields')
    if not raw or raw.lower() == 'all':
        return rows
    wanted = {t.strip() for t in raw.split(',') if t.strip()}
    if not wanted:
        return rows
    filtered = []
    for row in rows:
        filtered.append({k: v for k, v in row.items() if k in wanted})
    return filtered


class DicomWebStudies(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        params = dict(request.query_params)
        pagination = _Pagination(params)
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')

        if series_uid:
            rows = await self._query_instances(params, study_uid, series_uid)
            rows = _apply_includefield(rows, params)
            return DicomJsonResponse(json.dumps(rows))
        if study_uid:
            rows = await self._query_series(params, study_uid)
            rows = _apply_includefield(rows, params)
            return DicomJsonResponse(json.dumps(rows))

        rows, total = await self._query_studies(params, pagination)
        rows = _apply_includefield(rows, params)
        resp = DicomJsonResponse(json.dumps(rows))
        resp.headers['X-Total-Count'] = str(total)
        return resp

    async def _query_studies(self, params, pagination):
        where_clauses = []
        args = []
        idx = 1

        patient_id = params.get('PatientID')
        if patient_id:
            where_clauses.append(f"p.patient_id = ${idx}")
            args.append(patient_id)
            idx += 1

        patient_name = params.get('PatientName')
        if patient_name:
            # DICOMweb uses '*' wildcards; translate to SQL ILIKE. Leading
            # and trailing '*' become partial matches; a bare '*' matches all.
            like = patient_name.replace('*', '%')
            if like.strip('%') == '':
                like = '%'
            where_clauses.append(f"p.name ILIKE ${idx}")
            args.append(like)
            idx += 1

        accession = params.get('AccessionNumber')
        if accession:
            where_clauses.append(f"s.accession_number = ${idx}")
            args.append(accession)
            idx += 1

        study_uid = params.get('StudyInstanceUID')
        if study_uid:
            where_clauses.append(f"s.study_instance_uid = ${idx}")
            args.append(study_uid)
            idx += 1

        study_description = params.get('StudyDescription')
        if study_description:
            like = study_description.replace('*', '%')
            where_clauses.append(f"s.description ILIKE ${idx}")
            args.append(like)
            idx += 1

        modality = params.get('Modality')
        if modality:
            where_clauses.append(f"""EXISTS (
                SELECT 1 FROM series ser WHERE ser.study_id = s.id AND ser.modality = ${idx}
            )""")
            args.append(modality)
            idx += 1

        study_date = params.get('StudyDate')
        if study_date and '-' in study_date:
            start, _, end = study_date.partition('-')
            if start:
                where_clauses.append(f"s.study_date >= ${idx}")
                args.append(start)
                idx += 1
            if end:
                where_clauses.append(f"s.study_date <= ${idx}")
                args.append(end)
                idx += 1
        elif study_date:
            where_clauses.append(f"s.study_date = ${idx}")
            args.append(study_date)
            idx += 1

        where = ' AND '.join(where_clauses) if where_clauses else 'TRUE'

        async with get_conn() as conn:
            count_sql = f"""
                SELECT COUNT(*)
                FROM studies s
                JOIN patients p ON p.id = s.patient_id
                WHERE {where}
            """
            total = await conn.fetchval(count_sql, *args) or 0

            sql = f"""
                SELECT p.patient_id, p.name AS patient_name, p.birth_date AS patient_birth_date,
                       p.sex AS patient_sex, s.id AS study_db_id, s.study_id, s.description AS study_description,
                       s.study_instance_uid, s.accession_number, s.study_date
                FROM studies s
                JOIN patients p ON p.id = s.patient_id
                WHERE {where}
                ORDER BY s.id DESC
                LIMIT ${idx} OFFSET ${idx + 1}
            """
            args.append(pagination.limit)
            args.append(pagination.offset)

            rows = await conn.fetch(sql, *args)
            return [row_to_study_json(dict(r)) for r in rows], total

    async def _query_series(self, params, study_uid):
        async with get_conn() as conn:
            sql = """
                SELECT ser.number AS series_number, ser.modality, ser.description AS series_description,
                       ser.series_instance_uid
                FROM series ser
                JOIN studies s ON s.id = ser.study_id
                WHERE s.study_instance_uid = $1
                ORDER BY ser.number
            """
            rows = await conn.fetch(sql, study_uid)
            from dcm.dicom_json import row_to_series_json
            return [row_to_series_json(dict(r)) for r in rows]

    async def _query_instances(self, params, study_uid, series_uid):
        async with get_conn() as conn:
            sql = """
                SELECT f.sop_instance_uid, f.sop_class_uid, f.instance_number
                FROM files f
                JOIN series ser ON ser.id = f.series_id
                JOIN studies s ON s.id = ser.study_id
                WHERE s.study_instance_uid = $1 AND ser.series_instance_uid = $2
                  AND f.deleted = false
                ORDER BY f.name
            """
            rows = await conn.fetch(sql, study_uid, series_uid)
            from dcm.dicom_json import row_to_instance_json
            return [row_to_instance_json(dict(r)) for r in rows]

    @requires_permission(Permission.DICOMWEB_WRITE)
    async def post(self, request):
        body = await request.body()
        content_type = request.headers.get('content-type', '')

        parts = _parse_multipart_related(body, content_type)
        if not parts:
            err_body = {'error': {'code': 'EMPTY_REQUEST', 'message': 'No DICOM instances in request body'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

        # STOW-RS success report (PS3.18 §10.5): 00081190 RetrieveURL,
        # 00081198 Referenced SOP Sequence with 00081150/00081155 per stored
        # instance, 00081199 Failed SOP Sequence for any store failures.
        referenced = []
        failed = []
        for part_bytes in parts:
            try:
                buf = BytesIO(part_bytes)
                ds = dcmread(buf)
                buf.seek(0)
            except Exception:
                err_body = {'error': {'code': 'PARSE_ERROR', 'message': 'Malformed DICOM instance'}}
                return DicomJsonResponse(json.dumps(err_body), status_code=400)

            sop_uid = getattr(ds, 'SOPInstanceUID', None)
            if not sop_uid:
                err_body = {
                    'error': {'code': 'MISSING_SOP_INSTANCE_UID', 'message': 'Instance lacks SOPInstanceUID'},
                }
                return DicomJsonResponse(json.dumps(err_body), status_code=400)
            sop_class = str(getattr(ds, 'SOPClassUID', ''))

            modality = getattr(ds, 'Modality', '')
            if modality and not validate_modality(modality):
                err_body = {'error': {'code': 'INVALID_MODALITY', 'message': f'Invalid modality: {modality}'}}
                return DicomJsonResponse(json.dumps(err_body), status_code=400)

            ok = await store_instance(ds, buf)
            ref_sop = {
                '00081150': {'vr': 'UI', 'Value': [sop_class]},
                '00081155': {'vr': 'UI', 'Value': [str(sop_uid)]},
            }
            if ok:
                referenced.append(ref_sop)
            else:
                failed.append(ref_sop)

        report = {}
        if referenced:
            retrieve_url = str(request.base_url).rstrip('/') + '/dicomweb/studies'
            report['00081190'] = {'vr': 'UR', 'Value': [retrieve_url]}
            report['00081198'] = {'vr': 'SQ', 'Value': referenced}
        if failed:
            report['00081199'] = {'vr': 'SQ', 'Value': failed}

        if not referenced and failed:
            status_code = 409
        else:
            status_code = 200
        return DicomJsonResponse(json.dumps(report), status_code=status_code)


class DicomWebWado(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')
        instance_uid = request.path_params.get('instance_uid')

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return DicomJsonResponse(
                    json.dumps({'error': {'code': 'NO_STORAGE', 'message': 'No storage available'}}),
                    status_code=503,
                )

            if instance_uid:
                return await _wado_retrieve_instance(conn, master, instance_uid)

            if series_uid:
                return await _wado_retrieve_series(conn, master, study_uid, series_uid)

            return await _wado_retrieve_study(conn, master, study_uid)


class DicomWebWadoUri(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        params = dict(request.query_params)
        if params.get('requestType') != 'WADO':
            err_body = {'error': {'code': 'INVALID_REQUEST', 'message': 'requestType must be WADO'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

        study_uid = params.get('studyUID')
        series_uid = params.get('seriesUID')
        object_uid = params.get('objectUID')

        if not study_uid or not object_uid:
            err_body = {'error': {'code': 'MISSING_PARAMS', 'message': 'studyUID and objectUID are required'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return DicomJsonResponse(
                    json.dumps({'error': {'code': 'NO_STORAGE', 'message': 'No storage available'}}),
                    status_code=503,
                )

            if object_uid:
                return await _wado_retrieve_instance(conn, master, object_uid)

            if series_uid:
                return await _wado_retrieve_series(conn, master, study_uid, series_uid)

            return await _wado_retrieve_study(conn, master, study_uid)


async def _wado_retrieve_instance(conn, master, instance_uid):
    row = await conn.fetchrow("""
        SELECT rf.id, rf.location, f.name, f.patient_id, f.study_id, f.series_id,
               f.meta, rf.meta AS replica_meta
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        WHERE f.sop_instance_uid = $1 AND rf.replica_id = $2 AND f.deleted = false
        LIMIT 1
    """, instance_uid, master['id'])
    if not row:
        err_body = {'error': {'code': 'NOT_FOUND', 'message': 'Instance not found'}}
        return DicomJsonResponse(json.dumps(err_body), status_code=404)

    storage = await Storage.get(master)
    file_data = dict(row)
    file_data['meta'] = json.loads(file_data.get('meta') or '{}')
    file_data['replica_meta'] = json.loads(file_data.get('replica_meta') or '{}')
    path = await storage.fetch(file_data)
    async with aiofiles.open(path, 'rb') as f:
        content = await f.read()
    return Response(content, media_type='application/dicom')


async def _wado_retrieve_series(conn, master, study_uid, series_uid):
    rows = await conn.fetch("""
        SELECT rf.id, rf.location, f.name, f.patient_id, f.study_id, f.series_id,
               f.meta, rf.meta AS replica_meta
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        JOIN series s ON s.id = f.series_id
        JOIN studies st ON st.id = s.study_id
        WHERE st.study_instance_uid = $1
          AND s.series_instance_uid = $2
          AND rf.replica_id = $3
          AND f.deleted = false
    """, study_uid, series_uid, master['id'])
    if not rows:
        err_body = {'error': {'code': 'NOT_FOUND', 'message': 'Series not found'}}
        return DicomJsonResponse(json.dumps(err_body), status_code=404)
    return await _wado_build_multipart(rows, master)


async def _wado_retrieve_study(conn, master, study_uid):
    rows = await conn.fetch("""
        SELECT rf.id, rf.location, f.name, f.patient_id, f.study_id, f.series_id,
               f.meta, rf.meta AS replica_meta
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        JOIN studies st ON st.id = f.study_id
        WHERE st.study_instance_uid = $1 AND rf.replica_id = $2 AND f.deleted = false
    """, study_uid, master['id'])
    if not rows:
        err_body = {'error': {'code': 'NOT_FOUND', 'message': 'Study not found'}}
        return DicomJsonResponse(json.dumps(err_body), status_code=404)
    return await _wado_build_multipart(rows, master)


async def _wado_build_multipart(rows, master):
    storage = await Storage.get(master)
    boundary = 'WADO_BOUNDARY'

    async def _iter_chunks():
        for row in rows:
            file_data = dict(row)
            file_data['meta'] = json.loads(file_data.get('meta') or '{}')
            file_data['replica_meta'] = json.loads(file_data.get('replica_meta') or '{}')
            path = await storage.fetch(file_data)
            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()
            yield (
                f'--{boundary}\r\n'
                f'Content-Type: application/dicom\r\n\r\n'
            ).encode('latin-1') + content + b'\r\n'
        yield f'--{boundary}--\r\n'.encode('latin-1')

    return StreamingResponse(
        _iter_chunks(),
        media_type=f'multipart/related; type=application/dicom; boundary={boundary}',
    )


def _parse_multipart_related(body, content_type):
    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part[len('boundary='):]
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            break

    if not boundary:
        return [body]

    boundary_bytes = boundary.encode('latin-1')
    parts = []
    for raw in body.split(b'--' + boundary_bytes):
        raw = raw.strip(b'\r\n').strip()
        if raw == b'' or raw == b'--':
            continue
        # Header terminator may be CRLFCRLF or LFLF depending on the client;
        # only the DICOM part body follows the blank line.
        header_end = raw.find(b'\r\n\r\n')
        sep_len = 4
        if header_end == -1:
            header_end = raw.find(b'\n\n')
            sep_len = 2
        if header_end == -1:
            continue
        part_body = raw[header_end + sep_len:]
        if b'Content-Type: application/dicom' in raw[:header_end]:
            parts.append(part_body)

    return parts
