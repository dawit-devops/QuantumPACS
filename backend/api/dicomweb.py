"""DICOMweb REST API endpoints — implements QIDO-RS (search), WADO-RS (retrieve), and STOW-RS
(store) conforming to the DICOMweb standard. Provides JSON and bulk-data access to studies,
series, and instances stored in the QuantumPACS backend."""
import asyncio
import json
import threading
import time
import zipfile
from collections import defaultdict
from io import BytesIO

import aiofiles
from pydicom import dcmread
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response, StreamingResponse

from api.rbac import requires_permission
from api.permissions import Permission
from db.conn import get_conn
from db.audit_log import AuditLog
from db.replica import Replica
from dcm.dicom_json import row_to_study_json
from dcm.store import store_instance
from storage.storage import Storage

_STOW_ATTEMPTS = defaultdict(list)
_STOW_MAX_PER_IP = 30
_STOW_WINDOW_SECONDS = 60

# Files are streamed to the client in bounded chunks; a large CT/MR study is
# never materialized in memory at once (HI-06).
_WADO_CHUNK_SIZE = 1024 * 1024

# As-stored retrieval only. `transferSyntax=*` means "as stored"; an explicit
# syntax we don't transcode to is Not Acceptable per PS3.18 §11.4.1.
_STORED_TRANSFER_SYNTAX = '1.2.840.10008.1.2.1'


class _StowPartTooLarge(Exception):
    """A single STOW multipart part exceeded the configured size cap."""


def _stow_allowed(ip):
    """Per-IP token bucket for STOW-RS ingest (in-memory, best effort).

    STOW carries bulk data, so it needs abuse protection — but unlike login,
    a Redis round-trip on every store is wasteful. A bounded in-memory window
    keeps hot modems honest without adding latency.
    """
    if not ip:
        return True
    now = time.monotonic()
    cutoff = now - _STOW_WINDOW_SECONDS
    _STOW_ATTEMPTS[ip] = [t for t in _STOW_ATTEMPTS[ip] if t > cutoff]
    if len(_STOW_ATTEMPTS[ip]) >= _STOW_MAX_PER_IP:
        return False
    _STOW_ATTEMPTS[ip].append(now)
    return True

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
    MAX_LIMIT = 1000

    def __init__(self, params):
        limit = params.get('limit')
        offset = params.get('offset')
        # Cap the page size: an uncapped limit lets a single QIDO request
        # materialize the entire study archive.
        self.limit = min(int(limit) if limit and limit.isdigit() else 100, self.MAX_LIMIT)
        self.offset = int(offset) if offset and offset.isdigit() else 0


# QIDO-RS accepts tags either by DICOM keyword or by (group,element) hex
# (e.g. `0020000D` for StudyInstanceUID). Normalize the hex forms to the
# keywords the query builders branch on.
_HEX_TAG_TO_KEYWORD = {
    '00080016': 'SOPClassUID',
    '00080018': 'SOPInstanceUID',
    '00080020': 'StudyDate',
    '00080050': 'AccessionNumber',
    '00080060': 'Modality',
    '00081030': 'StudyDescription',
    '00081050': 'PerformingPhysicianName',
    '00081090': 'ReferringPhysicianName',
    '00100010': 'PatientName',
    '00100020': 'PatientID',
    '0020000D': 'StudyInstanceUID',
    '0020000E': 'SeriesInstanceUID',
    '00200011': 'SeriesNumber',
    '00200013': 'InstanceNumber',
    '00080052': 'QueryRetrieveLevel',
}


def _normalize_params(params):
    normalized = dict(params)
    for hex_tag, keyword in _HEX_TAG_TO_KEYWORD.items():
        if hex_tag in normalized and keyword not in normalized:
            normalized[keyword] = normalized[hex_tag]
    return normalized


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
        params = _normalize_params(dict(request.query_params))
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

        referring_physician = params.get('ReferringPhysicianName')
        if referring_physician:
            like = referring_physician.replace('*', '%')
            where_clauses.append(f"s.referring_physician ILIKE ${idx}")
            args.append(like)
            idx += 1

        performing_physician = params.get('PerformingPhysicianName')
        if performing_physician:
            like = performing_physician.replace('*', '%')
            where_clauses.append(f"s.performing_physician ILIKE ${idx}")
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
                       s.study_instance_uid, s.accession_number, s.study_date,
                       s.referring_physician, s.performing_physician
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
        where = 's.study_instance_uid = $1'
        args = [study_uid]
        idx = 2

        series_uid = params.get('SeriesInstanceUID')
        if series_uid:
            where += f' AND ser.series_instance_uid = ${idx}'
            args.append(series_uid)
            idx += 1

        series_number = params.get('SeriesNumber')
        if series_number:
            where += f' AND ser.number = ${idx}'
            args.append(series_number)
            idx += 1

        modality = params.get('Modality')
        if modality:
            where += f' AND ser.modality = ${idx}'
            args.append(modality)
            idx += 1

        series_description = params.get('SeriesDescription')
        if series_description:
            where += f' AND ser.description ILIKE ${idx}'
            args.append(series_description.replace('*', '%'))
            idx += 1

        async with get_conn() as conn:
            sql = f"""
                SELECT ser.number AS series_number, ser.modality, ser.description AS series_description,
                       ser.series_instance_uid
                FROM series ser
                JOIN studies s ON s.id = ser.study_id
                WHERE {where}
                ORDER BY ser.number
            """
            rows = await conn.fetch(sql, *args)
            from dcm.dicom_json import row_to_series_json
            return [row_to_series_json(dict(r)) for r in rows]

    async def _query_instances(self, params, study_uid, series_uid):
        where = 's.study_instance_uid = $1 AND ser.series_instance_uid = $2 AND f.deleted = false'
        args = [study_uid, series_uid]
        idx = 3

        sop_uid = params.get('SOPInstanceUID')
        if sop_uid:
            where += f' AND f.sop_instance_uid = ${idx}'
            args.append(sop_uid)
            idx += 1

        sop_class = params.get('SOPClassUID')
        if sop_class:
            where += f' AND f.sop_class_uid = ${idx}'
            args.append(sop_class)
            idx += 1

        instance_number = params.get('InstanceNumber')
        if instance_number:
            where += f' AND f.instance_number = ${idx}'
            args.append(instance_number)
            idx += 1

        async with get_conn() as conn:
            sql = f"""
                SELECT f.sop_instance_uid, f.sop_class_uid, f.instance_number
                FROM files f
                JOIN series ser ON ser.id = f.series_id
                JOIN studies s ON s.id = ser.study_id
                WHERE {where}
                ORDER BY f.name
            """
            rows = await conn.fetch(sql, *args)
            from dcm.dicom_json import row_to_instance_json
            return [row_to_instance_json(dict(r)) for r in rows]

    @requires_permission(Permission.DICOMWEB_WRITE)
    async def post(self, request):
        # STOW-RS can carry whole studies; the Content-Length pre-check
        # rejects oversized payloads before any body is read (HI-06), and
        # the body itself is parsed part-by-part from the request stream so
        # only one instance is in memory at a time.
        from config import config as app_config
        max_mb = int(app_config.get('max_stow_size_mb', '2048'))
        max_bytes = max_mb * 1024 * 1024
        size_hint = request.headers.get('content-length')
        if size_hint and size_hint.isdigit() and int(size_hint) > max_bytes:
            err_body = {'error': {'code': 'PAYLOAD_TOO_LARGE', 'message': f'STOW payload exceeds {max_mb}MB limit'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=413)

        content_type = request.headers.get('content-type', '')

        # PS3.18 §10.5: the study UID in the request path must match the
        # instances being stored. Enforce it before any write happens.
        path_study_uid = request.path_params.get('study_uid')

        # STOW-RS is a machine-to-machine API authenticated by token; the
        # browser CSRF token does not apply. Guard against abuse instead with
        # a per-IP token bucket.
        if not _stow_allowed(request.client.host if request.client else ''):
            err_body = {'error': {'code': 'RATE_LIMITED', 'message': 'Too many STOW requests, try again later'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=429)

        # STOW-RS success report (PS3.18 §10.5): 00081190 RetrieveURL,
        # 00081198 Referenced SOP Sequence with 00081150/00081155 per stored
        # instance, 00081199 Failed SOP Sequence for any store failures.
        referenced = []
        failed = []
        try:
            async for part_bytes in _iter_stow_parts(request, content_type, max_bytes):
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

                if path_study_uid:
                    instance_study_uid = str(getattr(ds, 'StudyInstanceUID', ''))
                    if instance_study_uid != path_study_uid:
                        err_body = {
                            'error': {
                                'code': 'STUDY_UID_MISMATCH',
                                'message': f'Instance StudyInstanceUID {instance_study_uid} does not match path {path_study_uid}',
                            },
                        }
                        return DicomJsonResponse(json.dumps(err_body), status_code=409)

                modality = getattr(ds, 'Modality', '')
                if modality and not validate_modality(modality):
                    err_body = {'error': {'code': 'INVALID_MODALITY', 'message': f'Invalid modality: {modality}'}}
                    return DicomJsonResponse(json.dumps(err_body), status_code=400)

                tenant_slug = getattr(request.state, 'tenant_slug', '')
                tenant_info = getattr(request.state, 'tenant', None) or {}
                tenant_id = str(tenant_info.get('id', '')) if tenant_info.get('id') else ''
                ok = await store_instance(
                    ds, buf,
                    tenant_id=tenant_id,
                    tenant_slug=tenant_slug,
                    tenant_info=tenant_info,
                )
                ref_sop = {
                    '00081150': {'vr': 'UI', 'Value': [sop_class]},
                    '00081155': {'vr': 'UI', 'Value': [str(sop_uid)]},
                }
                if ok:
                    referenced.append(ref_sop)
                else:
                    failed.append(ref_sop)
        except _StowPartTooLarge:
            err_body = {'error': {'code': 'PAYLOAD_TOO_LARGE', 'message': f'STOW payload exceeds {max_mb}MB limit'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=413)

        if not referenced and not failed:
            err_body = {'error': {'code': 'EMPTY_REQUEST', 'message': 'No DICOM instances in request body'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

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


def _check_transfer_syntax(request):
    """Only as-stored retrieval is implemented.

    PS3.18 §11.4.1: `transferSyntax=*` (or absent) means as-stored; an
    explicit syntax we don't transcode to is Not Acceptable (406).
    """
    ts = request.query_params.get('transferSyntax', '')
    if not ts or ts == '*':
        return True
    return ts == _STORED_TRANSFER_SYNTAX


def _wants_metadata(accept):
    """Accept-header negotiation: application/dicom+json → metadata (ME-02)."""
    accept = (accept or '').lower()
    return 'dicom+json' in accept


def _instance_metadata(file_data):
    """Compact PS3.18 metadata object for a stored instance.

    We persist a curated attribute subset (dcm/file.get_meta); the JSON uses
    the same tag/vr/Value shape QIDO-RS returns rather than inventing a
    parallel format.
    """
    meta = file_data.get('meta') or {}

    def _set(tag, vr, key, default=''):
        val = str(file_data.get(key) or meta.get(key) or default)
        if val:
            md[tag] = {'vr': vr, 'Value': [val]}
        else:
            md[tag] = {'vr': vr}

    md = {}
    _set('00080016', 'UI', 'sop_class_uid')
    _set('00080018', 'UI', 'sop_instance_uid')
    _set('00080020', 'DA', 'study_date')
    _set('00080060', 'CS', 'modality')
    _set('00081030', 'LO', 'study_description')
    _set('00081050', 'PN', 'performing_physician')
    _set('00081090', 'PN', 'referring_physician')
    _set('00100010', 'PN', 'patient_name')
    _set('00100020', 'LO', 'patient_id')
    _set('00100030', 'DA', 'patient_birth_date')
    _set('00100040', 'CS', 'patient_sex')
    _set('0020000D', 'UI', 'study_instance_uid')
    _set('0020000E', 'UI', 'series_instance_uid')
    _set('00200011', 'IS', 'series_number')
    _set('00200013', 'IS', 'instance_number')
    return md


class DicomWebWado(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')
        instance_uid = request.path_params.get('instance_uid')

        if not _check_transfer_syntax(request):
            err_body = {'error': {'code': 'NOT_ACCEPTABLE', 'message': 'Unsupported transferSyntax (as-stored only)'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=406)

        metadata = _wants_metadata(request.headers.get('accept', ''))

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return DicomJsonResponse(
                    json.dumps({'error': {'code': 'NO_STORAGE', 'message': 'No storage available'}}),
                    status_code=503,
                )

            if instance_uid:
                return await _wado_retrieve_instance(conn, master, instance_uid, metadata)

            if series_uid:
                return await _wado_retrieve_series(conn, master, study_uid, series_uid, metadata)

            return await _wado_retrieve_study(conn, master, study_uid, metadata)

    @requires_permission(Permission.DICOMWEB_WRITE)
    async def delete(self, request):
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')
        instance_uid = request.path_params.get('instance_uid')

        async with get_conn() as conn:
            if instance_uid:
                await conn.execute("""
                    UPDATE files SET deleted = true
                    WHERE sop_instance_uid = $1 AND deleted = false
                """, instance_uid)
            elif series_uid:
                await conn.execute("""
                    UPDATE files SET deleted = true
                    WHERE deleted = false AND series_id IN (
                        SELECT id FROM series WHERE series_instance_uid = $1
                    )
                """, series_uid)
            elif study_uid:
                await conn.execute("""
                    UPDATE files SET deleted = true
                    WHERE deleted = false AND series_id IN (
                        SELECT id FROM series WHERE study_id IN (
                            SELECT id FROM studies WHERE study_instance_uid = $1
                        )
                    )
                """, study_uid)
            else:
                err_body = {'error': {'code': 'MISSING_PARAMS', 'message': 'Nothing to delete'}}
                return DicomJsonResponse(json.dumps(err_body), status_code=400)

            await AuditLog(conn).log_event(
                'dicomweb.delete',
                getattr(request.user, 'id', None),
                'study' if not instance_uid and not series_uid else 'series' if not instance_uid else 'instance',
                instance_uid or series_uid or study_uid,
                details={'study': study_uid or '-', 'series': series_uid or '-', 'instance': instance_uid or '-'},
            )
        return Response(status_code=204)


class DicomWebWadoUri(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        params = dict(request.query_params)
        if params.get('requestType') != 'WADO':
            err_body = {'error': {'code': 'INVALID_REQUEST', 'message': 'requestType must be WADO'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

        study_uid = params.get('studyUID', '')
        series_uid = params.get('seriesUID', '')
        object_uid = params.get('objectUID', '')

        if not study_uid and not series_uid and not object_uid:
            err_body = {'error': {'code': 'MISSING_PARAMS', 'message': 'At least one of studyUID, seriesUID, objectUID is required'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)

        if not _check_transfer_syntax(request):
            err_body = {'error': {'code': 'NOT_ACCEPTABLE', 'message': 'Unsupported transferSyntax (as-stored only)'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=406)

        # WADO-URI objectUID is mandatory only at instance level; studyUID
        # alone retrieves the study, studyUID+seriesUID the series
        # (PS3.18 §8.7.2). contentTypes=application/dicom+json opts into
        # metadata (ME-02/ME-07).
        metadata = 'dicom+json' in (params.get('contentTypes', '') or '').lower()

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                return DicomJsonResponse(
                    json.dumps({'error': {'code': 'NO_STORAGE', 'message': 'No storage available'}}),
                    status_code=503,
                )

            if object_uid:
                # Cross-check: an objectUID that names an instance of a
                # different study is an error, not a silent 404 (ME-07).
                return await _wado_retrieve_instance(conn, master, object_uid, metadata, study_uid)

            if series_uid:
                return await _wado_retrieve_series(conn, master, study_uid, series_uid, metadata)

            return await _wado_retrieve_study(conn, master, study_uid, metadata)


async def _wado_retrieve_instance(conn, master, instance_uid, metadata=False, study_uid=None):
    _WADO_COLS = (
        'rf.id, rf.location, f.name, '
        'p.patient_id, st.study_id, '
        'f.meta, rf.meta AS replica_meta, '
        'f.sop_instance_uid, f.sop_class_uid, f.instance_number, '
        'ser.number AS series_number, '
        'f.meta->>\'series_instance_uid\' AS series_instance_uid, '
        'f.meta->>\'study_instance_uid\' AS study_instance_uid, '
        'f.meta->>\'study_date\' AS study_date, '
        'f.meta->>\'modality\' AS modality, '
        'f.meta->>\'patient_name\' AS patient_name, '
        'f.meta->>\'patient_birth_date\' AS patient_birth_date, '
        'f.meta->>\'patient_sex\' AS patient_sex, '
        'f.meta->>\'study_description\' AS study_description, '
        'f.meta->>\'referring_physician\' AS referring_physician, '
        'f.meta->>\'performing_physician\' AS performing_physician'
    )
    if study_uid:
        row = await conn.fetchrow(f"""
            SELECT {_WADO_COLS}
            FROM replica_files rf
            JOIN files f ON f.id = rf.file_id
            JOIN patients p ON p.id = f.patient_id
            JOIN series ser ON ser.id = f.series_id
            JOIN studies st ON st.id = ser.study_id
            WHERE f.sop_instance_uid = $1 AND rf.replica_id = $2 AND f.deleted = false
              AND st.study_instance_uid = $3
            LIMIT 1
        """, instance_uid, master['id'], study_uid)
    else:
        row = await conn.fetchrow(f"""
            SELECT {_WADO_COLS}
            FROM replica_files rf
            JOIN files f ON f.id = rf.file_id
            JOIN patients p ON p.id = f.patient_id
            JOIN studies st ON st.id = f.study_id
            JOIN series ser ON ser.id = f.series_id
            WHERE f.sop_instance_uid = $1 AND rf.replica_id = $2 AND f.deleted = false
            LIMIT 1
        """, instance_uid, master['id'])
    if not row:
        if study_uid:
            err_body = {'error': {'code': 'STUDY_UID_MISMATCH', 'message': 'objectUID is not a member of the given study'}}
            return DicomJsonResponse(json.dumps(err_body), status_code=400)
        err_body = {'error': {'code': 'NOT_FOUND', 'message': 'Instance not found'}}
        return DicomJsonResponse(json.dumps(err_body), status_code=404)

    file_data = dict(row)
    file_data['meta'] = json.loads(file_data.get('meta') or '{}')
    file_data['replica_meta'] = json.loads(file_data.get('replica_meta') or '{}')

    if metadata:
        return DicomJsonResponse(json.dumps([_instance_metadata(file_data)]))

    storage = await Storage.get(master)
    path = await storage.fetch(file_data)

    async def _iter_file():
        async with aiofiles.open(path, 'rb') as f:
            while True:
                chunk = await f.read(_WADO_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(_iter_file(), media_type='application/dicom')


async def _wado_retrieve_series(conn, master, study_uid, series_uid, metadata=False):
    rows = await conn.fetch("""
        SELECT rf.id, rf.location, f.name,
               p.patient_id, st.study_id,
               f.meta, rf.meta AS replica_meta,
               f.sop_instance_uid, f.sop_class_uid, f.instance_number,
               s.number AS series_number,
               f.meta->>'series_instance_uid' AS series_instance_uid,
               f.meta->>'study_instance_uid' AS study_instance_uid,
               f.meta->>'study_date' AS study_date,
               f.meta->>'modality' AS modality,
               f.meta->>'patient_name' AS patient_name,
               f.meta->>'patient_birth_date' AS patient_birth_date,
               f.meta->>'patient_sex' AS patient_sex,
               f.meta->>'study_description' AS study_description,
               f.meta->>'referring_physician' AS referring_physician,
               f.meta->>'performing_physician' AS performing_physician
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        JOIN patients p ON p.id = f.patient_id
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
    if metadata:
        file_data = [dict(r) for r in rows]
        for fd in file_data:
            fd['meta'] = json.loads(fd.get('meta') or '{}')
            fd['replica_meta'] = json.loads(fd.get('replica_meta') or '{}')
        return DicomJsonResponse(json.dumps([_instance_metadata(fd) for fd in file_data]))
    return await _wado_build_multipart(rows, master)


async def _wado_retrieve_study(conn, master, study_uid, metadata=False):
    rows = await conn.fetch("""
        SELECT rf.id, rf.location, f.name,
               p.patient_id, st.study_id,
               f.meta, rf.meta AS replica_meta,
               f.sop_instance_uid, f.sop_class_uid, f.instance_number,
               ser.number AS series_number,
               f.meta->>'series_instance_uid' AS series_instance_uid,
               f.meta->>'study_instance_uid' AS study_instance_uid,
               f.meta->>'study_date' AS study_date,
               f.meta->>'modality' AS modality,
               f.meta->>'patient_name' AS patient_name,
               f.meta->>'patient_birth_date' AS patient_birth_date,
               f.meta->>'patient_sex' AS patient_sex,
               f.meta->>'study_description' AS study_description,
               f.meta->>'referring_physician' AS referring_physician,
               f.meta->>'performing_physician' AS performing_physician
        FROM replica_files rf
        JOIN files f ON f.id = rf.file_id
        JOIN patients p ON p.id = f.patient_id
        JOIN series ser ON ser.id = f.series_id
        JOIN studies st ON st.id = f.study_id
        WHERE st.study_instance_uid = $1 AND rf.replica_id = $2 AND f.deleted = false
    """, study_uid, master['id'])
    if not rows:
        err_body = {'error': {'code': 'NOT_FOUND', 'message': 'Study not found'}}
        return DicomJsonResponse(json.dumps(err_body), status_code=404)
    if metadata:
        file_data = [dict(r) for r in rows]
        for fd in file_data:
            fd['meta'] = json.loads(fd.get('meta') or '{}')
            fd['replica_meta'] = json.loads(fd.get('replica_meta') or '{}')
        return DicomJsonResponse(json.dumps([_instance_metadata(fd) for fd in file_data]))
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
            yield (
                f'--{boundary}\r\n'
                f'Content-Type: application/dicom\r\n\r\n'
            ).encode('latin-1')
            async with aiofiles.open(path, 'rb') as f:
                while True:
                    chunk = await f.read(_WADO_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            yield b'\r\n'
        yield f'--{boundary}--\r\n'.encode('latin-1')

    return StreamingResponse(
        _iter_chunks(),
        media_type=f'multipart/related; type=application/dicom; boundary={boundary}',
    )


class _ZipStream:
    """File-like sink that hands zipfile output to a StreamingResponse.

    The zip is assembled in a worker thread (zipfile is synchronous); bytes
    are pushed to an asyncio queue drained by the response, so memory stays
    bounded to one compressed part at a time (HI-08).
    """

    def __init__(self):
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()

    def write(self, data):
        self._loop.call_soon_threadsafe(self._queue.put_nowait, data)
        return len(data)

    def flush(self):
        pass

    def close(self):
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)


class DicomWebArchive(HTTPEndpoint):
    """Streamed study/series ZIP export (HI-08).

    Deflated, named by UID (`study/series/instance.dcm`) with a metadata.json
    manifest — the "download entire study" pattern from the pacs-workflow
    skill. DICOMDIR generation is a deliberate later phase.
    """

    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        study_uid = request.path_params.get('study_uid')
        series_uid = request.path_params.get('series_uid')

        async with get_conn() as conn:
            master = await Replica(conn).master()
            if not master:
                err_body = {'error': {'code': 'NO_STORAGE', 'message': 'No storage available'}}
                return DicomJsonResponse(json.dumps(err_body), status_code=503)

            if series_uid:
                rows = await conn.fetch("""
                    SELECT f.id, f.name, f.sop_instance_uid, f.sop_class_uid, f.instance_number,
                           f.meta, ser.series_instance_uid, ser.number AS series_number,
                           p.patient_id, st.study_id
                    FROM files f
                    JOIN patients p ON p.id = f.patient_id
                    JOIN series ser ON ser.id = f.series_id
                    JOIN studies st ON st.id = ser.study_id
                    JOIN replica_files rf ON rf.file_id = f.id
                    WHERE st.study_instance_uid = $1
                      AND ser.series_instance_uid = $2
                      AND rf.replica_id = $3
                      AND f.deleted = false
                    ORDER BY ser.number, f.instance_number
                """, study_uid, series_uid, master['id'])
            else:
                rows = await conn.fetch("""
                    SELECT f.id, f.name, f.sop_instance_uid, f.sop_class_uid, f.instance_number,
                           f.meta, ser.series_instance_uid, ser.number AS series_number,
                           p.patient_id, st.study_id
                    FROM files f
                    JOIN patients p ON p.id = f.patient_id
                    JOIN series ser ON ser.id = f.series_id
                    JOIN studies st ON st.id = ser.study_id
                    JOIN replica_files rf ON rf.file_id = f.id
                    WHERE st.study_instance_uid = $1
                      AND rf.replica_id = $2
                      AND f.deleted = false
                    ORDER BY ser.number, f.instance_number
                """, study_uid, master['id'])

            if not rows:
                err_body = {'error': {'code': 'NOT_FOUND', 'message': 'No instances found for archive'}}
                return DicomJsonResponse(json.dumps(err_body), status_code=404)

            storage = await Storage.get(master)
            prepared = []
            for row in rows:
                file_data = dict(row)
                file_data['meta'] = json.loads(file_data.get('meta') or '{}')
                file_data['replica_meta'] = {}
                path = await storage.fetch(file_data)
                prepared.append((path, row))

        sink = _ZipStream()
        filename = f'series-{series_uid}.zip' if series_uid else f'study-{study_uid}.zip'

        def _build():
            zf = zipfile.ZipFile(sink, 'w', zipfile.ZIP_DEFLATED)
            for path, row in prepared:
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                except OSError:
                    continue
                name = (
                    f"{row['series_instance_uid']}/{row['sop_instance_uid']}.dcm"
                )
                zf.writestr(name, data)
            manifest = {
                'study_instance_uid': study_uid,
                'series_instance_uid': series_uid or None,
                'instance_count': len(prepared),
            }
            zf.writestr('metadata.json', json.dumps(manifest, indent=2))
            zf.close()
            sink.close()

        thread = threading.Thread(target=_build, daemon=True)
        thread.start()

        async def _drain():
            while True:
                chunk = await sink._queue.get()
                if chunk is None:
                    break
                yield chunk
            thread.join()

        return StreamingResponse(
            _drain(),
            media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
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


def _extract_boundary(content_type):
    """Return the multipart boundary from a Content-Type header, if any."""
    for segment in content_type.split(';'):
        segment = segment.strip()
        if segment.startswith('boundary='):
            boundary = segment[len('boundary='):]
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            return boundary
    return None


async def _iter_stow_parts(request, content_type, max_part_bytes):
    """Stream STOW-RS multipart bodies part-by-part (HI-06).

    The full body is never buffered: each yielded part (one DICOM instance)
    is capped at `max_part_bytes`, keeping memory proportional to the largest
    instance rather than the whole study. Raises _StowPartTooLarge when a
    single part exceeds the cap.
    """
    boundary = _extract_boundary(content_type)
    if not boundary:
        # A single DICOM body with no boundary (PS3.18 §6.2.1.1).
        buf = b''
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > max_part_bytes:
                raise _StowPartTooLarge
        if buf:
            yield buf
        return

    marker = b'--' + boundary.encode('latin-1')
    buf = b''
    it = request.stream()

    async def _read_more():
        nonlocal buf
        chunk = await it.__anext__()
        buf += chunk
        # Allow slack for the marker + boundary preamble; the cap protects
        # against oversized parts, not exact accounting.
        if len(buf) > max_part_bytes + len(marker) + 65536:
            raise _StowPartTooLarge

    # Skip the prologue before the first boundary.
    while marker not in buf:
        try:
            await _read_more()
        except StopAsyncIteration:
            return
    buf = buf[buf.find(marker) + len(marker):]

    while True:
        # Read part headers up to the blank-line terminator.
        while True:
            crlf = buf.find(b'\r\n\r\n')
            lf = buf.find(b'\n\n')
            if crlf != -1 and (lf == -1 or crlf <= lf):
                headers_end, sep_len = crlf, 4
            elif lf != -1:
                headers_end, sep_len = lf, 2
            else:
                try:
                    await _read_more()
                except StopAsyncIteration:
                    return
                continue
            break
        headers = buf[:headers_end]
        buf = buf[headers_end + sep_len:]
        if b'Content-Type: application/dicom' not in headers:
            # Non-DICOM part (e.g. metadata) — skip to the next boundary.
            while marker not in buf:
                try:
                    await _read_more()
                except StopAsyncIteration:
                    return
            idx = buf.find(marker)
            buf = buf[idx + len(marker):]
            continue

        # Accumulate the part body until the next boundary marker.
        while marker not in buf:
            try:
                await _read_more()
            except StopAsyncIteration:
                return
        idx = buf.find(marker)
        part_body = buf[:idx]
        buf = buf[idx + len(marker):]
        if part_body.startswith(b'\r\n'):
            part_body = part_body[2:]
        elif part_body.startswith(b'\n'):
            part_body = part_body[1:]
        if part_body.endswith(b'\r\n'):
            part_body = part_body[:-2]
        elif part_body.endswith(b'\n'):
            part_body = part_body[:-1]
        if part_body:
            yield bytes(part_body)
        # Closing boundary is '--boundary--'.
        if buf.startswith(b'--'):
            return
