"""FHIR R4 API endpoints — Patient, ImagingStudy, and DocumentReference resources
with search, read, create, update, and delete operations conforming to the HL7 FHIR
release 4 specification for healthcare data interoperability."""
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
    raise RuntimeError('Use parameterized queries instead of _quote()')

log = get_logger(__name__)

FHIR_MIME = 'application/fhir+json'


async def _get_fhir_base_url():
    try:
        from db.conn import get_conn
        from db.fhir_config import FhirConfig
        async with get_conn() as conn:
            cfg = FhirConfig(conn)
            raw = await cfg.get_all()
            return raw.get('base_url', 'http://localhost:8080/api/fhir')
    except Exception:
        return 'http://localhost:8080/api/fhir'


async def _is_fhir_enabled():
    try:
        from db.conn import get_conn
        from db.fhir_config import FhirConfig
        async with get_conn() as conn:
            cfg = FhirConfig(conn)
            raw = await cfg.get_all()
            return raw.get('enabled', 'false') == 'true'
    except Exception:
        return True


class FhirJsonResponse(Response):
    media_type = FHIR_MIME

    def render(self, content):
        return json.dumps(content, ensure_ascii=False, allow_nan=False, default=str).encode('utf-8')


async def _build_bundle(entries, total=None, params=None):
    base_url = await _get_fhir_base_url()
    bundle = {
        'resourceType': 'Bundle',
        'type': 'searchset',
        'total': total if total is not None else len(entries),
        'entry': [{'resource': e, 'search': {'mode': 'match'}} for e in entries],
    }
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        bundle['link'] = [
            {'relation': 'self', 'url': f'{base_url}?{qs}'},
        ]
    return bundle


def _patient_resource(row) -> dict:
    meta = row.get('meta') or {}
    name_parts = (row['name'] or '').split('^')
    family = name_parts[0] if name_parts else ''
    given = name_parts[1:2] if len(name_parts) > 1 else []
    resource = {
        'resourceType': 'Patient',
        'id': str(row['patient_id']),
        'identifier': [{
            'use': 'usual',
            'type': {'coding': [{'system': 'http://hl7.org/fhir/v2/0203', 'code': 'MR'}]},
            'value': row['patient_id'],
        }],
        'name': [{'family': family, 'given': given}],
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


async def _imagingstudy_resource(study) -> dict:
    fhir_base = await _get_fhir_base_url()
    dicomweb_base = fhir_base.replace('/fhir', '/dicomweb')
    resource = {
        'resourceType': 'ImagingStudy',
        'id': study.get('study_instance_uid') or study['study_id'],
        'identifier': [{'value': study['study_id']}],
        'status': 'available',
        'subject': {'reference': f'Patient/{study["_patient_logical_id"]}'},
        'endpoint': [{'reference': dicomweb_base}],
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
        enabled = await _is_fhir_enabled()
        if not enabled:
            return FhirJsonResponse({
                'resourceType': 'OperationOutcome',
                'issue': [{'severity': 'error', 'code': 'forbidden', 'diagnostics': 'FHIR server is disabled'}],
            }, status_code=503)

        base_url = await _get_fhir_base_url()
        try:
            from db.conn import get_conn
            from db.fhir_config import FhirConfig
            async with get_conn() as conn:
                cfg = FhirConfig(conn)
                raw = await cfg.get_all()
                publisher = raw.get('publisher', 'QuantumPACS')
        except Exception:
            publisher = 'QuantumPACS'

        capability = {
            'resourceType': 'CapabilityStatement',
            'status': 'active',
            'date': '2026-07-29',
            'publisher': publisher,
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


class FhirPatientRoot(HTTPEndpoint):
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

            conds, vals, idx = _apply_last_updated(params, q, 'patients', 1)
            if conds:
                q = q.where(PseudoColumn(f" {' AND '.join(conds)}"))

            if limit:
                rows = await p.conn.fetch(str(q.limit(limit)), *vals)
            else:
                rows = await p.fetch(q)
            rows = [dict(r) for r in rows]

        resources = [_patient_resource(r) for r in rows]
        bundle = await _build_bundle(resources, len(rows), params)
        return FhirJsonResponse(bundle)

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await request.json()
        if not isinstance(body, dict):
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Invalid JSON body'}]}, status_code=400)
        patient_id = _extract_identifier(body.get('identifier'))
        if not patient_id:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'required', 'diagnostics': 'Patient identifier is required'}]}, status_code=422)
        patient_name = _parse_fhir_name(body.get('name'))
        birth_date = (body.get('birthDate') or '')[:10]
        gender = body.get('gender', '')
        sex_map = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': ''}
        sex = sex_map.get(gender, gender[:1].upper() if gender else '')

        async with get_conn() as conn:
            from db.patient import Patient as PatientModel
            p = PatientModel(conn)
            await p.insert_or_select({
                'patient_id': patient_id,
                'patient_name': patient_name,
                'patient_birth_date': birth_date,
                'patient_sex': sex,
            })
            row = await PatientModel(conn).get_extra(str(
                await conn.fetchval("SELECT id FROM patients WHERE patient_id = $1", patient_id)
            ))

        return FhirJsonResponse(_patient_resource(row), status_code=201)


class FhirPatientResource(HTTPEndpoint):
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

    @requires_permission(Permission.PATIENT_WRITE)
    async def put(self, request):
        patient_id = request.path_params.get('id')
        if not patient_id:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Missing patient ID'}]}, status_code=400)
        body = await request.json()
        if not isinstance(body, dict):
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Invalid JSON body'}]}, status_code=400)

        async with get_conn() as conn:
            existing = await conn.fetchval("SELECT id FROM patients WHERE patient_id = $1", patient_id)
            if not existing:
                return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Patient {patient_id} not found'}]}, status_code=404)

            patient_name = _parse_fhir_name(body.get('name'))
            birth_date = (body.get('birthDate') or '')[:10]
            gender = body.get('gender', '')
            sex_map = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': ''}
            sex = sex_map.get(gender, gender[:1].upper() if gender else '')

            sets = []
            vals = []
            idx = 1
            if patient_name:
                sets.append(f"name = ${idx}")
                vals.append(patient_name)
                idx += 1
            if birth_date:
                sets.append(f"birth_date = ${idx}")
                vals.append(birth_date)
                idx += 1
            if sex:
                sets.append(f"sex = ${idx}")
                vals.append(sex)
                idx += 1
            if sets:
                vals.append(patient_id)
                await conn.execute(f"UPDATE patients SET {', '.join(sets)} WHERE patient_id = ${idx}", *vals)

            row = await Patient(conn).get_extra(patient_id)

        return FhirJsonResponse(_patient_resource(row))

    @requires_permission(Permission.PATIENT_WRITE)
    async def delete(self, request):
        patient_id = request.path_params.get('id')
        if not patient_id:
            return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'invalid', 'diagnostics': 'Missing patient ID'}]}, status_code=400)
        async with get_conn() as conn:
            existing = await conn.fetchval("SELECT id FROM patients WHERE patient_id = $1", patient_id)
            if not existing:
                return FhirJsonResponse({'resourceType': 'OperationOutcome', 'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Patient {patient_id} not found'}]}, status_code=404)
            await conn.execute("DELETE FROM patients WHERE patient_id = $1", patient_id)
        return FhirJsonResponse(None, status_code=204)


def _parse_fhir_name(name_list):
    if not name_list:
        return ''
    name = name_list[0]
    parts = []
    if name.get('family'):
        parts.append(name['family'])
    if name.get('given'):
        given = name['given']
        if isinstance(given, list):
            parts.extend(given)
        else:
            parts.append(given)
    return '^'.join(parts) if parts else ''


def _extract_identifier(identifiers):
    if not identifiers:
        return ''
    for id_ in identifiers:
        val = id_.get('value', '')
        if val:
            return val
    return ''


def _apply_last_updated(params, query, table_ref, idx):
    conds = []
    vals = []
    if '_lastUpdated' in params:
        val = params['_lastUpdated']
        prefix = ''
        for pfx in ('ge', 'gt', 'le', 'lt', 'eq', 'ne', 'sa', 'eb', 'ap'):
            if val.startswith(pfx):
                prefix = pfx
                val = val[len(pfx):]
                break
        op_map = {'ge': '>=', 'gt': '>', 'le': '<=', 'lt': '<', 'eq': '=', 'ne': '!='}
        op = op_map.get(prefix, '=')
        conds.append(f"{table_ref}.updated_at {op} ${idx}::timestamptz")
        vals.append(val)
        idx += 1
    return conds, vals, idx


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
        return FhirJsonResponse(await _imagingstudy_resource(study))


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

            search_conds = []
            search_vals = []
            if 'patient' in params:
                pid = params['patient'].replace('Patient/', '')
                search_conds.append(f"EXISTS (SELECT 1 FROM patients pa WHERE pa.id = studies.patient_id AND pa.patient_id = ${len(search_vals) + 1})")
                search_vals.append(pid)
            if 'accession' in params:
                q = q.where(st.table.accession_number == params['accession'])
            if 'modality' in params:
                search_conds.append(f"EXISTS (SELECT 1 FROM series se WHERE se.study_id = studies.id AND se.modality = ${len(search_vals) + 1})")
                search_vals.append(params['modality'])
            if search_conds:
                q = q.where(PseudoColumn(' AND '.join(search_conds)))

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

            lu_conds, lu_vals, _ = _apply_last_updated(params, q, 'studies', len(search_vals) + 1)
            if lu_conds:
                q = q.where(PseudoColumn(f" {' AND '.join(lu_conds)}"))

            if limit:
                rows = await st.conn.fetch(str(q.limit(limit)), *search_vals, *lu_vals)
            else:
                rows = await st.fetch(q)

            studies = []
            for r in rows:
                study = dict(r)
                study['_patient_logical_id'] = await _patient_logical_id(conn, study.get('patient_id', 0))
                series_rows = await _fetch_series_for_study(conn, study['id'])
                study['_series'] = series_rows
                studies.append(study)

        resources = [await _imagingstudy_resource(s) for s in studies]
        bundle = await _build_bundle(resources, len(studies), params)
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
            if 'period' in params:
                period = params['period']
                prefix = ''
                val = period
                for pfx in ('ge', 'gt', 'le', 'lt', 'eq', 'ne', 'sa', 'eb', 'ap'):
                    if period.startswith(pfx):
                        prefix = pfx
                        val = period[len(pfx):]
                        break
                op_map = {'ge': '>=', 'gt': '>', 'le': '<=', 'lt': '<', 'eq': '=', 'ne': '!='}
                op = op_map.get(prefix, '=')
                conds.append(f"sf.created {op} ${idx}::timestamptz")
                vals.append(val)
                idx += 1
            if '_lastUpdated' in params:
                lu_conds, lu_vals, idx = _apply_last_updated(params, query, 'sf', idx)
                conds.extend(lu_conds)
                vals.extend(lu_vals)
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
        bundle = await _build_bundle(resources, len(shares), params)
        return FhirJsonResponse(bundle)
