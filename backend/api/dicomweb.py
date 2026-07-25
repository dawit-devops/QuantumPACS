import json
from io import BytesIO

from pydicom import dcmread
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response

from api.rbac import requires_permission
from api.permissions import Permission
from db.conn import get_conn
from db.replica import Replica
from dcm.dicom_json import row_to_study_json
from dcm.store import store_instance
from storage.storage import Storage


class DicomJsonResponse(Response):
    media_type = 'application/dicom+json'


class _Pagination:
    def __init__(self, params):
        limit = params.get('limit')
        offset = params.get('offset')
        self.limit = int(limit) if limit and limit.isdigit() else 100
        self.offset = int(offset) if offset and offset.isdigit() else 0


class DicomWebStudies(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        params = dict(request.query_params)
        pagination = _Pagination(params)
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')

        if series_uid:
            rows = await self._query_instances(params, study_uid, series_uid)
            return DicomJsonResponse(json.dumps(rows))
        if study_uid:
            rows = await self._query_series(params, study_uid)
            return DicomJsonResponse(json.dumps(rows))

        rows, total = await self._query_studies(params, pagination)
        resp = DicomJsonResponse(json.dumps(rows))
        resp.headers['X-Total-Count'] = str(total)
        return resp

    async def _query_studies(self, params, pagination):
        patient_id = params.get('PatientID')
        accession = params.get('AccessionNumber')
        study_uid = params.get('StudyInstanceUID')

        where_clauses = []
        args = []
        idx = 1
        if patient_id:
            where_clauses.append(f"p.patient_id = ${idx}")
            args.append(patient_id)
            idx += 1
        if accession:
            where_clauses.append(f"s.accession_number = ${idx}")
            args.append(accession)
            idx += 1
        if study_uid:
            where_clauses.append(f"s.study_instance_uid = ${idx}")
            args.append(study_uid)
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
                       s.study_instance_uid, s.accession_number
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
                SELECT f.sop_instance_uid, f.meta
                FROM files f
                JOIN series ser ON ser.id = f.series_id
                JOIN studies s ON s.id = ser.study_id
                WHERE s.study_instance_uid = $1 AND ser.series_instance_uid = $2
                ORDER BY f.name
            """
            rows = await conn.fetch(sql, study_uid, series_uid)
            from dcm.dicom_json import row_to_instance_json
            result = []
            for r in rows:
                row = dict(r)
                if row.get('meta'):
                    meta = json.loads(row['meta'])
                    row['sop_class_uid'] = meta.get('SOPClassUID', '')
                    row['instance_number'] = meta.get('InstanceNumber', '')
                result.append(row_to_instance_json(row))
            return result

    @requires_permission(Permission.DICOMWEB_WRITE)
    async def post(self, request):
        body = await request.body()
        content_type = request.headers.get('content-type', '')

        parts = _parse_multipart_related(body, content_type)
        stored = []
        for part_bytes in parts:
            try:
                buf = BytesIO(part_bytes)
                ds = dcmread(buf)
                buf.seek(0)
            except Exception:
                return Response(
                    json.dumps({'error': 'Malformed DICOM instance'}),
                    status_code=400,
                    media_type='application/dicom+json',
                )
            ok = await store_instance(ds, buf)
            if ok:
                stored.append(str(ds.SOPInstanceUID))

        return DicomJsonResponse(json.dumps(stored))


class DicomWebWado(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')
        instance_uid = request.path_params.get('instance_uid')

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return Response(json.dumps({'error': 'No storage available'}), status_code=503)

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
            return Response(
                json.dumps({'error': 'requestType must be WADO'}),
                status_code=400,
            )

        study_uid = params.get('studyUID')
        series_uid = params.get('seriesUID')
        object_uid = params.get('objectUID')

        if not study_uid or not object_uid:
            return Response(
                json.dumps({'error': 'studyUID and objectUID are required'}),
                status_code=400,
            )

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return Response(json.dumps({'error': 'No storage available'}), status_code=503)

            if series_uid:
                return await _wado_retrieve_series(conn, master, study_uid, series_uid)

            return await _wado_retrieve_instance(conn, master, object_uid)


async def _wado_retrieve_instance(conn, master, instance_uid):
    row = await conn.fetchrow("""
        SELECT rf.id, rf.location, f.name, f.patient_id, f.study_id, f.series_id,
               f.meta, rf.meta AS replica_meta
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        WHERE f.sop_instance_uid = $1 AND rf.replica_id = $2
        LIMIT 1
    """, instance_uid, master['id'])
    if not row:
        return Response(json.dumps({'error': 'Instance not found'}), status_code=404)

    storage = await Storage.get(master)
    file_data = dict(row)
    file_data['meta'] = json.loads(file_data.get('meta') or '{}')
    file_data['replica_meta'] = json.loads(file_data.get('replica_meta') or '{}')
    path = await storage.fetch(file_data)
    with open(path, 'rb') as f:
        content = f.read()
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
    """, study_uid, series_uid, master['id'])
    if not rows:
        return Response(json.dumps({'error': 'Series not found'}), status_code=404)
    return await _wado_build_multipart(rows, master)


async def _wado_retrieve_study(conn, master, study_uid):
    rows = await conn.fetch("""
        SELECT rf.id, rf.location, f.name, f.patient_id, f.study_id, f.series_id,
               f.meta, rf.meta AS replica_meta
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        JOIN studies st ON st.id = f.study_id
        WHERE st.study_instance_uid = $1 AND rf.replica_id = $2
    """, study_uid, master['id'])
    if not rows:
        return Response(json.dumps({'error': 'Study not found'}), status_code=404)
    return await _wado_build_multipart(rows, master)


async def _wado_build_multipart(rows, master):
    storage = await Storage.get(master)
    boundary = 'WADO_BOUNDARY'
    body_parts = []
    for row in rows:
        file_data = dict(row)
        file_data['meta'] = json.loads(file_data.get('meta') or '{}')
        file_data['replica_meta'] = json.loads(file_data.get('replica_meta') or '{}')
        path = await storage.fetch(file_data)
        with open(path, 'rb') as f:
            content = f.read()
        part = (
            f'--{boundary}\r\n'
            f'Content-Type: application/dicom\r\n\r\n'
        ).encode('latin-1') + content + b'\r\n'
        body_parts.append(part)
    body_parts.append(f'--{boundary}--\r\n'.encode('latin-1'))
    body = b''.join(body_parts)

    return Response(
        body,
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
        header_end = raw.find(b'\r\n\r\n')
        if header_end == -1:
            continue
        part_body = raw[header_end + 4:]
        if b'Content-Type: application/dicom' in raw[:header_end]:
            parts.append(part_body)

    return parts
