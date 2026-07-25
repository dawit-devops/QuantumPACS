import json

from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response

from api.rbac import requires_permission
from api.permissions import Permission
from db.conn import get_conn
from dcm.dicom_json import row_to_study_json


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
