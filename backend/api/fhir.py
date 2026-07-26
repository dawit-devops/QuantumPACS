import json
from urllib.parse import parse_qs

from pypika import Query as PypikaQuery
from pypika import Table as PyTable
from pypika.pseudocolumns import PseudoColumn
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response

from api.rbac import requires_permission
from api.permissions import Permission
from db.conn import get_conn
from db.patient import Patient
from db.study import Study
from db.series import Series
from log import get_logger


def _quote(val):
    return "'" + str(val).replace("'", "''") + "'"

log = get_logger(__name__)

FHIR_MIME = 'application/fhir+json'
BASE_URL = 'http://localhost:8080/api/fhir'


class FhirJsonResponse(Response):
    media_type = FHIR_MIME

    def render(self, content):
        return json.dumps(content, ensure_ascii=False, allow_nan=False, default=str).encode('utf-8')


def _build_bundle(entries, total=None, params=None):
    bundle = {
        'resourceType': 'Bundle',
        'type': 'searchset',
        'total': total if total is not None else len(entries),
        'entry': [{'resource': e, 'search': {'mode': 'match'}} for e in entries],
    }
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        bundle['link'] = [
            {'relation': 'self', 'url': f'{BASE_URL}?{qs}'},
        ]
    return bundle


def _patient_resource(row) -> dict:
    meta = row.get('meta') or {}
    resource = {
        'resourceType': 'Patient',
        'id': str(row['patient_id']),
        'identifier': [{
            'use': 'usual',
            'type': {'coding': [{'system': 'http://hl7.org/fhir/v2/0203', 'code': 'MR'}]},
            'value': row['patient_id'],
        }],
        'name': [{'family': row['name'], 'given': [row['name']]}],
        'gender': row.get('sex', '').lower() if row.get('sex') else 'unknown',
    }
    if row.get('birth_date'):
        resource['birthDate'] = row['birth_date'][:10]
    if meta.get('sync_source'):
        resource['meta'] = {'tag': [{'code': meta['sync_source']}]}
    return resource


async def _patient_logical_id(conn, patient_db_id):
    pt = PyTable('patients')
    q = PypikaQuery.from_(pt).select(pt.patient_id).where(pt.id == patient_db_id)
    row = await conn.fetchrow(str(q))
    return row['patient_id'] if row else None


def _imagingstudy_resource(study) -> dict:
    resource = {
        'resourceType': 'ImagingStudy',
        'id': study.get('study_instance_uid') or study['study_id'],
        'identifier': [{'value': study['study_id']}],
        'status': 'available',
        'subject': {'reference': f'Patient/{study["_patient_logical_id"]}'},
    }
    if study.get('description'):
        resource['description'] = study['description']
    if study.get('accession_number'):
        resource['identifier'].append({
            'use': 'usual',
            'type': {'coding': [{'system': 'http://hl7.org/fhir/v2/0203', 'code': 'ACSN'}]},
            'value': study['accession_number'],
        })
    series_list = study.get('_series', [])
    if series_list:
        resource['series'] = []
        for s in series_list:
            sr = {
                'uid': s.get('series_instance_uid', ''),
                'number': int(s['number']) if s.get('number', '').isdigit() else 0,
                'modality': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': s.get('modality', '')},
            }
            if s.get('description'):
                sr['description'] = s['description']
            if s.get('_instances'):
                sr['instance'] = [{
                    'uid': inst.get('sop_instance_uid', ''),
                    'sopClass': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': inst.get('sop_class_uid', '')},
                    'number': int(inst.get('instance_number', 0)),
                } for inst in s['_instances']]
            resource['series'].append(sr)
    return resource


def _documentreference_resource(share) -> dict:
    pid = share.get('_patient_logical_id') or share.get('patient_id', '')
    created = share.get('created') or share.get('created_at', '')
    return {
        'resourceType': 'DocumentReference',
        'id': str(share['id']),
        'status': 'current',
        'type': {'coding': [{'system': 'http://loinc.org', 'code': '18748-4', 'display': 'Diagnostic Imaging Report'}]},
        'subject': {'reference': f'Patient/{pid}'},
        'content': [{
            'attachment': {'url': share.get('share_url', ''), 'contentType': 'application/dicom'},
        }],
        'date': created.isoformat() if hasattr(created, 'isoformat') else str(created),
    }


class FhirMetadata(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        capability = {
            'resourceType': 'CapabilityStatement',
            'status': 'active',
            'date': '2026-07-26',
            'publisher': 'QuantumPACS',
            'kind': 'instance',
            'software': {'name': 'QuantumPACS', 'version': '3.0.0'},
            'fhirVersion': '4.0.1',
            'format': ['application/fhir+json'],
            'rest': [{
                'mode': 'server',
                'resource': [
                    {
                        'type': 'Patient',
                        'interaction': [{'code': 'read'}, {'code': 'search-type'}],
                        'searchParam': [
                            {'name': 'identifier', 'type': 'token'},
                            {'name': 'name', 'type': 'string'},
                            {'name': 'birthdate', 'type': 'date'},
                        ],
                    },
                    {
                        'type': 'ImagingStudy',
                        'interaction': [{'code': 'read'}, {'code': 'search-type'}],
                        'searchParam': [
                            {'name': 'patient', 'type': 'reference'},
                            {'name': 'accession', 'type': 'token'},
                            {'name': 'modality', 'type': 'token'},
                            {'name': 'started', 'type': 'date'},
                        ],
                    },
                    {
                        'type': 'DocumentReference',
                        'interaction': [{'code': 'read'}, {'code': 'search-type'}],
                        'searchParam': [
                            {'name': 'patient', 'type': 'reference'},
                            {'name': 'type', 'type': 'token'},
                        ],
                    },
                ],
            }],
        }
        return FhirJsonResponse(capability)


class FhirPatientRead(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        patient_id = request.path_params.get('id')
        if not patient_id:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Missing patient ID'}]}, status_code=400)
        async with get_conn() as conn:
            p = Patient(conn)
            row = await p.get_extra(patient_id)
        if not row:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Patient {patient_id} not found'}]}, status_code=404)
        return FhirJsonResponse(_patient_resource(row))


class FhirPatientSearch(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

        async with get_conn() as conn:
            p = Patient(conn)
            q = p.select(p.table.star)

            if 'identifier' in params:
                q = q.where(p.table.patient_id == params['identifier'])
            if 'name' in params:
                q = q.where(p.table.name.ilike(f'%{params["name"]}%'))
            if 'birthdate' in params:
                q = q.where(p.table.birth_date == params['birthdate'])

            limit = None
            if '_count' in params:
                try:
                    limit = max(1, min(int(params['_count']), 100))
                except (ValueError, TypeError):
                    pass

            if '_sort' in params:
                direction = 'DESC' if params['_sort'].startswith('-') else 'ASC'
                field = params['_sort'].lstrip('-')
                allowed = {'patient_id': 'patient_id', 'name': 'name', 'birth_date': 'birth_date'}
                col = allowed.get(field, 'id')
                q = q.orderby(col, order=direction)

            if limit:
                rows = await p.conn.fetch(str(q.limit(limit)))
            else:
                rows = await p.fetch(q)
            rows = [dict(r) for r in rows]

        resources = [_patient_resource(r) for r in rows]
        bundle = _build_bundle(resources, len(rows), params)
        return FhirJsonResponse(bundle)


class FhirImagingStudyRead(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        study_uid = request.path_params.get('id')
        if not study_uid:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Missing study UID'}]}, status_code=400)
        async with get_conn() as conn:
            st = Study(conn)
            q = st.select(st.table.star).where(st.table.study_instance_uid == study_uid)
            row = await st.fetchone(q)
            if not row:
                return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Study {study_uid} not found'}]}, status_code=404)
            study = dict(row)
            study['_patient_logical_id'] = await _patient_logical_id(conn, study.get('patient_id', 0))
            series_rows = await _fetch_series_for_study(conn, study['id'])
            study['_series'] = series_rows
        return FhirJsonResponse(_imagingstudy_resource(study))


class FhirImagingStudySearch(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

        async with get_conn() as conn:
            st = Study(conn)
            q = st.select(st.table.star)

            if 'patient' in params:
                pid = params['patient'].replace('Patient/', '')
                q = q.where(PseudoColumn(f"EXISTS (SELECT 1 FROM patients pa WHERE pa.id = studies.patient_id AND pa.patient_id = {_quote(pid)})"))
            if 'accession' in params:
                q = q.where(st.table.accession_number == params['accession'])
            if 'modality' in params:
                q = q.where(PseudoColumn(f"EXISTS (SELECT 1 FROM series se WHERE se.study_id = studies.id AND se.modality = {_quote(params['modality'])})"))

            limit = None
            if '_count' in params:
                try:
                    limit = max(1, min(int(params['_count']), 100))
                except (ValueError, TypeError):
                    pass

            if '_sort' in params:
                direction = 'DESC' if params['_sort'].startswith('-') else 'ASC'
                field = params['_sort'].lstrip('-')
                allowed = {'study_instance_uid': 'study_instance_uid', 'accession_number': 'accession_number', 'description': 'description'}
                col = allowed.get(field, 'id')
                q = q.orderby(col, order=direction)

            if limit:
                rows = await st.conn.fetch(str(q.limit(limit)))
            else:
                rows = await st.fetch(q)

            studies = []
            for r in rows:
                study = dict(r)
                study['_patient_logical_id'] = await _patient_logical_id(conn, study.get('patient_id', 0))
                series_rows = await _fetch_series_for_study(conn, study['id'])
                study['_series'] = series_rows
                studies.append(study)

        resources = [_imagingstudy_resource(s) for s in studies]
        bundle = _build_bundle(resources, len(studies), params)
        return FhirJsonResponse(bundle)


async def _fetch_series_for_study(conn, study_db_id):
    sr = Series(conn)
    q = sr.select(sr.table.star).where(sr.table.study_id == study_db_id)
    rows = await sr.fetch(q)
    return [dict(r) for r in rows]


class FhirDocumentReferenceRead(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        doc_id = request.path_params.get('id')
        if not doc_id:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Missing document ID'}]}, status_code=400)
        try:
            doc_int = int(doc_id)
        except (ValueError, TypeError):
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Document {doc_id} not found'}]}, status_code=404)
        async with get_conn() as conn:
            row = await conn.fetchrow("""
                SELECT sf.*, pa.patient_id AS _patient_logical_id
                FROM shared_files sf
                JOIN files fi ON fi.id = sf.file_id
                JOIN patients pa ON pa.id = fi.patient_id
                WHERE sf.id = $1
            """, doc_int)
            if not row:
                return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Document {doc_id} not found'}]}, status_code=404)
            share = dict(row)
        return FhirJsonResponse(_documentreference_resource(share))


class FhirDocumentReferenceSearch(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

        async with get_conn() as conn:
            query = """
                SELECT sf.*, pa.patient_id AS _patient_logical_id
                FROM shared_files sf
                JOIN files fi ON fi.id = sf.file_id
                JOIN patients pa ON pa.id = fi.patient_id
            """
            conds = []
            vals = []
            idx = 1
            if 'patient' in params:
                conds.append(f"pa.patient_id = ${idx}")
                vals.append(params['patient'].replace('Patient/', ''))
                idx += 1
            if 'type' in params:
                conds.append(f"fi.meta->>'type' = ${idx}")
                vals.append(params['type'])
                idx += 1
            if conds:
                query += ' WHERE ' + ' AND '.join(conds)

            limit = None
            if '_count' in params:
                try:
                    limit = max(1, min(int(params['_count']), 100))
                except (ValueError, TypeError):
                    pass

            if limit:
                query += f' LIMIT {limit}'

            rows = await conn.fetch(query, *vals)
            shares = [dict(r) for r in rows]

        resources = [_documentreference_resource(s) for s in shares]
        bundle = _build_bundle(resources, len(shares), params)
        return FhirJsonResponse(bundle)
