"""FHIR R4 API endpoints — Patient, ImagingStudy, and DocumentReference resources
with search, read, create, update, and delete operations conforming to the HL7 FHIR
release 4 specification for healthcare data interoperability."""
import json
from datetime import date, datetime
from urllib.parse import parse_qs

from pypika import Query as PypikaQuery
from pypika import Table as PyTable
from pypika.pseudocolumns import PseudoColumn
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response

from api.rbac import requires_permission
from api.permissions import Permission
from api.dicomweb_proxy import _archive_wado_rs_base, proxy_enabled
from db.conn import get_conn
from db.patient import Patient
from db.study import Study
from db.series import Series
from db.files import Files
from log import get_logger


def _quote(val):
    raise RuntimeError('Use parameterized queries instead of _quote()')

log = get_logger(__name__)

FHIR_MIME = 'application/fhir+json'

VALID_GENDERS = {'male', 'female', 'other', 'unknown'}
_GENDER_TO_SEX = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': ''}
_SEX_TO_GENDER = {'M': 'male', 'F': 'female', 'O': 'other', '': 'unknown'}

_PREFIX_OPS = {'ge': '>=', 'gt': '>', 'le': '<=', 'lt': '<', 'eq': '=', 'ne': '!='}
_PREFIXES = ('ge', 'gt', 'le', 'lt', 'eq', 'ne', 'sa', 'eb', 'ap')

_PATIENT_SORT_FIELDS = {'patient_id': 'patient_id', 'name': 'name', 'birth_date': 'birth_date'}
_STUDY_SORT_FIELDS = {'study_instance_uid': 'study_instance_uid', 'accession_number': 'accession_number', 'description': 'description'}


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


def _fhir_disabled_response():
    return FhirJsonResponse({
        'resourceType': 'OperationOutcome',
        'issue': [{'severity': 'error', 'code': 'forbidden', 'diagnostics': 'FHIR server is disabled'}],
    }, status_code=503)


def _operation_outcome(code, diagnostics, status, severity='error'):
    return FhirJsonResponse({
        'resourceType': 'OperationOutcome',
        'issue': [{'severity': severity, 'code': code, 'diagnostics': diagnostics}],
    }, status_code=status)


class FhirJsonResponse(Response):
    media_type = FHIR_MIME

    def render(self, content):
        return json.dumps(content, ensure_ascii=False, allow_nan=False, default=str).encode('utf-8')


def _prefix_op(val):
    """Split a FHIR prefix (ge/gt/le/lt/eq/ne/sa/eb/ap) from a search value."""
    prefix = ''
    for pfx in _PREFIXES:
        if val.startswith(pfx):
            prefix = pfx
            val = val[len(pfx):]
            break
    return _PREFIX_OPS.get(prefix, '='), val


def _search_dt(val):
    """Parse a FHIR instant/date-ish search value into a datetime for asyncpg
    binding (asyncpg rejects strings for timestamptz params even with a cast)."""
    val = val.strip()
    try:
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    except ValueError:
        pass
    if len(val) == 4:
        return datetime(int(val), 1, 1)
    if len(val) == 7:
        return datetime(int(val[:4]), int(val[5:7]), 1)
    return datetime.combine(date.fromisoformat(val), datetime.min.time())


def _search_date(val):
    """Parse a FHIR date (YYYY[-MM[-DD]]) into a date object."""
    val = val.strip()
    if len(val) == 4:
        return date(int(val), 1, 1)
    if len(val) == 7:
        return date(int(val[:4]), int(val[5:7]), 1)
    return date.fromisoformat(val)


def _paging(params):
    limit = None
    offset = 0
    if '_count' in params:
        try:
            limit = max(1, min(int(params['_count']), 100))
        except (ValueError, TypeError):
            pass
    if '_offset' in params:
        try:
            offset = max(0, int(params['_offset']))
        except (ValueError, TypeError):
            pass
    return limit, offset


def _with_offset(params, offset):
    copy = dict(params)
    copy['_offset'] = str(offset)
    copy.setdefault('_count', '100')
    return '&'.join(f'{k}={v}' for k, v in copy.items())


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
        links = [
            {'relation': 'self', 'url': f'{base_url}?{qs}'},
        ]
        count = params.get('_count')
        if count and count.isdigit():
            count = int(count)
            offset = int(params['_offset']) if params.get('_offset', '').isdigit() else 0
            links.append({'relation': 'first', 'url': f'{base_url}?{_with_offset(params, 0)}'})
            if total is not None and offset + count < total:
                links.append({'relation': 'next', 'url': f'{base_url}?{_with_offset(params, offset + count)}'})
        bundle['link'] = links
    return bundle


def _patient_resource(row) -> dict:
    raw_meta = row.get('meta') or '{}'
    # asyncpg returns jsonb columns as text unless a codec is registered —
    # parse before touching keys (live E2E caught a str.get AttributeError).
    meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
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
        'gender': _SEX_TO_GENDER.get((row.get('sex') or '').upper(), 'unknown'),
    }
    if row.get('birth_date'):
        resource['birthDate'] = row['birth_date'][:10]
    updated_at = row.get('updated_at')
    if updated_at:
        iso = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else str(updated_at)
        resource['meta'] = {'versionId': iso, 'lastUpdated': iso}
    if meta.get('sync_source'):
        resource.setdefault('meta', {})['tag'] = [{'code': meta['sync_source']}]
    return resource


def _etag_from_row(row):
    updated = row.get('updated_at')
    if not updated:
        return None
    iso = updated.isoformat() if hasattr(updated, 'isoformat') else str(updated)
    return f'W/"{iso}"'


async def _patient_logical_id(conn, patient_db_id):
    pt = PyTable('patients')
    q = PypikaQuery.from_(pt).select(pt.patient_id).where(pt.id == patient_db_id)
    row = await conn.fetchrow(str(q))
    return row['patient_id'] if row else None


async def _patient_by_logical_id(conn, patient_id):
    """Resolve a Patient by its logical (DICOM) id and load its full extra row.

    get_extra() keys on the integer surrogate id, so lookup the surrogate first —
    passing the logical id straight through crashed with InvalidTextRepresentation.
    """
    db_id = await conn.fetchval('SELECT id FROM patients WHERE patient_id = $1', patient_id)
    if not db_id:
        return None
    return await Patient(conn).get_extra(str(db_id))


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
    if study.get('study_date'):
        sd = str(study['study_date'])
        if len(sd) == 8:
            resource['started'] = f'{sd[0:4]}-{sd[4:6]}-{sd[6:8]}'
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
        # Proxy mode: nested series endpoint points at the archive WADO-RS
        # base (ADR-028 Phase 3) so a DICOMweb client can pull series
        # instances straight from dcm4chee; local mode keeps the QP base.
        series_endpoint = _archive_wado_rs_base() if proxy_enabled() else dicomweb_base
        resource['series'] = []
        for s in series_list:
            sr = {
                'uid': s.get('series_instance_uid', ''),
                'number': int(s['number']) if s.get('number', '').isdigit() else 0,
                'modality': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': s.get('modality', '')},
                'endpoint': [{'reference': series_endpoint}],
            }
            if s.get('description'):
                sr['description'] = s['description']
            if s.get('_instances'):
                sr['instance'] = [{
                    'uid': inst.get('sop_instance_uid', ''),
                    'sopClass': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': inst.get('sop_class_uid', '')},
                    'number': int(inst['instance_number']) if str(inst.get('instance_number', '')).isdigit() else 0,
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
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()

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
                        'interaction': [{'code': 'read'}, {'code': 'search-type'}, {'code': 'create'}, {'code': 'update'}, {'code': 'delete'}],
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
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()

        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

        async with get_conn() as conn:
            conds = []
            vals = []
            idx = 1
            if 'identifier' in params:
                ident = params['identifier']
                if '|' in ident:
                    ident = ident.split('|', 1)[1]
                conds.append(f"patients.patient_id = ${idx}")
                vals.append(ident)
                idx += 1
            if 'name' in params:
                conds.append(f'patients.name ILIKE ${idx}')
                vals.append(f'%{params["name"]}%')
                idx += 1
            if 'birthdate' in params:
                op, val = _prefix_op(params['birthdate'])
                conds.append(f'patients.birth_date {op} ${idx}')
                vals.append(_search_date(val).strftime('%Y%m%d'))
                idx += 1
            if '_lastUpdated' in params:
                op, val = _prefix_op(params['_lastUpdated'])
                conds.append(f'patients.updated_at {op} ${idx}')
                vals.append(_search_dt(val))
                idx += 1

            where = ' WHERE ' + ' AND '.join(conds) if conds else ''
            total = await conn.fetchval(f'SELECT COUNT(*) FROM patients{where}', *vals)

            q = PypikaQuery.from_(PyTable('patients')).select(PyTable('patients').star)
            if conds:
                q = q.where(PseudoColumn(' AND '.join(conds)))
            if '_sort' in params:
                direction = 'DESC' if params['_sort'].startswith('-') else 'ASC'
                field = params['_sort'].lstrip('-')
                col = _PATIENT_SORT_FIELDS.get(field, 'id')
                q = q.orderby(col, order=direction)
            limit, offset = _paging(params)
            if limit:
                q = q.limit(limit)
            if offset:
                q = q.offset(offset)
            rows = await conn.fetch(str(q), *vals)
            rows = [dict(r) for r in rows]

        resources = [_patient_resource(r) for r in rows]
        bundle = await _build_bundle(resources, total, params)
        return FhirJsonResponse(bundle)

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()

        try:
            body = await request.json()
        except Exception:
            return _operation_outcome('invalid', 'Invalid JSON body', 400)
        if not isinstance(body, dict):
            return _operation_outcome('invalid', 'Invalid JSON body', 400)
        resource_type = body.get('resourceType')
        if resource_type and resource_type != 'Patient':
            return _operation_outcome('invalid', f"Expected resourceType 'Patient', got '{resource_type}'", 400)
        patient_id = _extract_identifier(body.get('identifier'))
        if not patient_id:
            return _operation_outcome('required', 'Patient identifier is required', 422)
        gender = body.get('gender', '')
        if gender and gender not in VALID_GENDERS:
            return _operation_outcome('value', f"Invalid gender '{gender}' — expected male|female|other|unknown", 422)
        patient_name = _parse_fhir_name(body.get('name'))
        birth_date = (body.get('birthDate') or '')[:10]
        sex = _GENDER_TO_SEX.get(gender, '')

        async with get_conn() as conn:
            from db.patient import Patient as PatientModel
            existing = await conn.fetchval('SELECT id FROM patients WHERE patient_id = $1', patient_id)
            if existing:
                row = await PatientModel(conn).get_extra(str(existing))
                status = 200
            else:
                await PatientModel(conn).insert_or_select({
                    'patient_id': patient_id,
                    'patient_name': patient_name,
                    'patient_birth_date': birth_date,
                    'patient_sex': sex,
                })
                db_id = await conn.fetchval('SELECT id FROM patients WHERE patient_id = $1', patient_id)
                row = await PatientModel(conn).get_extra(str(db_id))
                status = 201

        base = await _get_fhir_base_url()
        return FhirJsonResponse(
            _patient_resource(row),
            status_code=status,
            headers={'Location': f'{base}/Patient/{patient_id}'},
        )


class FhirPatientResource(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()
        patient_id = request.path_params.get('id')
        if not patient_id:
            return _operation_outcome('invalid', 'Missing patient ID', 400)
        async with get_conn() as conn:
            row = await _patient_by_logical_id(conn, patient_id)
        if not row:
            return _operation_outcome('not-found', f'Patient {patient_id} not found', 404)
        headers = {}
        etag = _etag_from_row(row)
        if etag:
            headers['ETag'] = etag
        return FhirJsonResponse(_patient_resource(row), headers=headers)

    @requires_permission(Permission.PATIENT_WRITE)
    async def put(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()
        patient_id = request.path_params.get('id')
        if not patient_id:
            return _operation_outcome('invalid', 'Missing patient ID', 400)
        try:
            body = await request.json()
        except Exception:
            return _operation_outcome('invalid', 'Invalid JSON body', 400)
        if not isinstance(body, dict):
            return _operation_outcome('invalid', 'Invalid JSON body', 400)
        resource_type = body.get('resourceType')
        if resource_type and resource_type != 'Patient':
            return _operation_outcome('invalid', f"Expected resourceType 'Patient', got '{resource_type}'", 400)

        async with get_conn() as conn:
            db_id = await conn.fetchval('SELECT id FROM patients WHERE patient_id = $1', patient_id)
            if not db_id:
                return _operation_outcome('not-found', f'Patient {patient_id} not found', 404)
            current = await Patient(conn).get_extra(str(db_id))
            if not current:
                return _operation_outcome('not-found', f'Patient {patient_id} not found', 404)

            etag = _etag_from_row(current)
            if etag:
                if_match = request.headers.get('if-match')
                if if_match and if_match.strip() != etag:
                    return _operation_outcome('conflict', 'If-Match version mismatch', 412)

            gender = body.get('gender', '')
            if gender and gender not in VALID_GENDERS:
                return _operation_outcome('value', f"Invalid gender '{gender}' — expected male|female|other|unknown", 422)
            patient_name = _parse_fhir_name(body.get('name'))
            birth_date = (body.get('birthDate') or '')[:10]
            sex = _GENDER_TO_SEX.get(gender, '')

            sets = []
            vals = []
            idx = 1
            if patient_name:
                sets.append(f'name = ${idx}')
                vals.append(patient_name)
                idx += 1
            if birth_date:
                sets.append(f'birth_date = ${idx}')
                vals.append(birth_date)
                idx += 1
            if sex:
                sets.append(f'sex = ${idx}')
                vals.append(sex)
                idx += 1
            if sets:
                vals.append(db_id)
                await conn.execute(f'UPDATE patients SET {", ".join(sets)} WHERE id = ${idx}', *vals)

            row = await Patient(conn).get_extra(str(db_id))

        headers = {}
        etag = _etag_from_row(row)
        if etag:
            headers['ETag'] = etag
        return FhirJsonResponse(_patient_resource(row), headers=headers)

    @requires_permission(Permission.PATIENT_WRITE)
    async def delete(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()
        patient_id = request.path_params.get('id')
        if not patient_id:
            return _operation_outcome('invalid', 'Missing patient ID', 400)
        async with get_conn() as conn:
            db_id = await conn.fetchval('SELECT id FROM patients WHERE patient_id = $1', patient_id)
            if not db_id:
                return _operation_outcome('not-found', f'Patient {patient_id} not found', 404)
            has_dependents = await conn.fetchval(
                'SELECT EXISTS (SELECT 1 FROM studies WHERE patient_id = $1) '
                'OR EXISTS (SELECT 1 FROM files WHERE patient_id = $1)',
                db_id,
            )
            if has_dependents:
                return _operation_outcome(
                    'conflict',
                    'Patient has imaging studies; deletion refused to protect clinical data',
                    409,
                )
            await conn.execute('DELETE FROM patients WHERE id = $1', db_id)
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


class FhirImagingStudyRead(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()
        study_uid = request.path_params.get('id')
        if not study_uid:
            return _operation_outcome('invalid', 'Missing study UID', 400)
        async with get_conn() as conn:
            st = Study(conn)
            q = st.select(st.table.star).where(st.table.study_instance_uid == study_uid)
            row = await st.fetchone(q)
            if not row:
                return _operation_outcome('not-found', f'Study {study_uid} not found', 404)
            study = dict(row)
            study['_patient_logical_id'] = await _patient_logical_id(conn, study.get('patient_id', 0))
            series_rows = await _fetch_series_for_study(conn, study['id'])
            study['_series'] = series_rows
        return FhirJsonResponse(await _imagingstudy_resource(study))


class FhirImagingStudySearch(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()

        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

        async with get_conn() as conn:
            search_conds = []
            search_vals = []
            idx = 1
            if 'patient' in params:
                pid = params['patient'].replace('Patient/', '')
                search_conds.append(f"EXISTS (SELECT 1 FROM patients pa WHERE pa.id = studies.patient_id AND pa.patient_id = ${idx})")
                search_vals.append(pid)
                idx += 1
            if 'accession' in params:
                search_conds.append(f'studies.accession_number = ${idx}')
                search_vals.append(params['accession'])
                idx += 1
            if 'modality' in params:
                search_conds.append(f"EXISTS (SELECT 1 FROM series se WHERE se.study_id = studies.id AND se.modality = ${idx})")
                search_vals.append(params['modality'])
                idx += 1
            if 'started' in params:
                op, val = _prefix_op(params['started'])
                # study_date is DICOM text (YYYYMMDD) — normalize FHIR dates
                # into that form so lexicographic comparison is correct.
                search_conds.append(f'studies.study_date {op} ${idx}')
                search_vals.append(_search_date(val).strftime('%Y%m%d'))
                idx += 1
            if '_lastUpdated' in params:
                op, val = _prefix_op(params['_lastUpdated'])
                search_conds.append(f'studies.updated_at {op} ${idx}')
                search_vals.append(_search_dt(val))
                idx += 1

            where = ' WHERE ' + ' AND '.join(search_conds) if search_conds else ''
            total = await conn.fetchval(f'SELECT COUNT(*) FROM studies{where}', *search_vals)

            q = PypikaQuery.from_(PyTable('studies')).select(PyTable('studies').star)
            if search_conds:
                q = q.where(PseudoColumn(' AND '.join(search_conds)))
            if '_sort' in params:
                direction = 'DESC' if params['_sort'].startswith('-') else 'ASC'
                field = params['_sort'].lstrip('-')
                col = _STUDY_SORT_FIELDS.get(field, 'id')
                q = q.orderby(col, order=direction)
            limit, offset = _paging(params)
            if limit:
                q = q.limit(limit)
            if offset:
                q = q.offset(offset)
            rows = await conn.fetch(str(q), *search_vals)
            rows = [dict(r) for r in rows]

            studies = []
            for r in rows:
                study = dict(r)
                study['_patient_logical_id'] = await _patient_logical_id(conn, study.get('patient_id', 0))
                series_rows = await _fetch_series_for_study(conn, study['id'])
                study['_series'] = series_rows
                studies.append(study)

        resources = [await _imagingstudy_resource(s) for s in studies]
        bundle = await _build_bundle(resources, total, params)
        return FhirJsonResponse(bundle)


async def _fetch_series_for_study(conn, study_db_id):
    sr = Series(conn)
    q = sr.select(sr.table.star).where(sr.table.study_id == study_db_id)
    rows = await sr.fetch(q)
    series_rows = []
    for r in rows:
        s = dict(r)
        s['_instances'] = await _fetch_instances_for_series(conn, s['id'])
        series_rows.append(s)
    return series_rows


async def _fetch_instances_for_series(conn, series_db_id):
    fl = Files(conn)
    q = (
        fl.select(
            fl.table.sop_instance_uid,
            fl.table.meta,
        )
        .where(fl.table.series_id == series_db_id)
        # noqa: E712 — pypika Field == bool is a SQL comparison (deleted = false),
        # not a Python identity check; is_(False) does not exist on pypika fields.
        .where(fl.table.deleted == False)  # noqa: E712
        .where(fl.table.indexed == True)  # noqa: E712
    )
    rows = await fl.fetch(q)
    out = []
    for r in rows:
        raw = r.get('meta') or '{}'
        try:
            meta = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except (ValueError, TypeError):
            meta = {}
        out.append({
            'sop_instance_uid': r.get('sop_instance_uid') or meta.get('sop_instance_uid', ''),
            'sop_class_uid': meta.get('sop_class_uid', ''),
            'instance_number': meta.get('instance_number', ''),
        })
    return out


class FhirDocumentReferenceRead(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()
        doc_id = request.path_params.get('id')
        if not doc_id:
            return _operation_outcome('invalid', 'Missing document ID', 400)
        try:
            doc_int = int(doc_id)
        except (ValueError, TypeError):
            return _operation_outcome('not-found', f'Document {doc_id} not found', 404)
        async with get_conn() as conn:
            row = await conn.fetchrow("""
                SELECT sf.*, pa.patient_id AS _patient_logical_id
                FROM shared_files sf
                JOIN files fi ON fi.id = sf.file_id
                JOIN patients pa ON pa.id = fi.patient_id
                WHERE sf.id = $1
            """, doc_int)
            if not row:
                return _operation_outcome('not-found', f'Document {doc_id} not found', 404)
            share = dict(row)
        return FhirJsonResponse(_documentreference_resource(share))


class FhirDocumentReferenceSearch(HTTPEndpoint):
    @requires_permission(Permission.FILE_READ)
    async def get(self, request):
        if not await _is_fhir_enabled():
            return _fhir_disabled_response()

        params = {}
        if request.url.query:
            qs = parse_qs(request.url.query)
            for k, v in qs.items():
                params[k] = v[0] if v else ''

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
            conds.append(f'pa.patient_id = ${idx}')
            vals.append(params['patient'].replace('Patient/', ''))
            idx += 1
        if 'type' in params:
            conds.append(f"fi.meta->>'type' = ${idx}")
            vals.append(params['type'])
            idx += 1
        if 'period' in params:
            op, val = _prefix_op(params['period'])
            conds.append(f'sf.created {op} ${idx}')
            vals.append(_search_dt(val))
            idx += 1
        if '_lastUpdated' in params:
            op, val = _prefix_op(params['_lastUpdated'])
            conds.append(f'sf.created {op} ${idx}')
            vals.append(_search_dt(val))
            idx += 1
        where = ' WHERE ' + ' AND '.join(conds) if conds else ''

        async with get_conn() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM shared_files sf"
                " JOIN files fi ON fi.id = sf.file_id"
                " JOIN patients pa ON pa.id = fi.patient_id" + where,
                *vals,
            )

            limit, offset = _paging(params)
            paged = ''
            if limit:
                paged = f' LIMIT {limit}'
            if offset:
                paged += f' OFFSET {offset}'

            rows = await conn.fetch(query + where + paged, *vals)
            shares = [dict(r) for r in rows]

        resources = [_documentreference_resource(s) for s in shares]
        bundle = await _build_bundle(resources, total, params)
        return FhirJsonResponse(bundle)
