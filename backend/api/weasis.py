"""Weasis desktop-viewer launch endpoint (ADR-028 Phase 3).

`GET /api/weasis/launch?studyUID=...` authorizes the request against the
QuantumPACS `files` table (like /dicomweb/admin*), then 302-redirects to
the weasis-pacs-connector's client-only launch URL. `&cdb` marks the launch
as client-driven — the connector hands the study UIDs to the desktop
client instead of serving a web page.

Disabled when `weasis_enabled=false` (404) so deployments without the
connector never expose the redirect target.
"""
from starlette.endpoints import HTTPEndpoint
from starlette.responses import RedirectResponse

import httpx

from api.dicomweb_proxy import proxy_enabled
from api.rbac import requires_permission
from api.permissions import Permission
from api.response import not_found, ok
from config import config
from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)


def _weasis_enabled() -> bool:
    return str(config.get('weasis_enabled', 'false')).lower() in ('1', 'true', 'yes', 'on')


async def _archive_authorized(study_uid='', patient_id=''):
    """Proxy-mode authz: the study/patient must exist in the dcm4chee archive.

    In proxy mode the archive is the store of truth (ADR-028 R7) and tenant
    scoping is intentionally not applied, so archive existence is the
    authorization signal — same surface the /dicomweb/* proxy serves. The QP
    `files` table check below would 404 fresh archive-only studies until the
    self-heal sync imports them (up to dcm4chee_sync_interval + export).
    """
    base = str(config.get('dcm4chee_url', 'http://localhost:8082/dcm4chee-arc')).rstrip('/')
    ae = config.get('dcm4chee_ae', 'DCM4CHEE')
    if study_uid:
        path = f'{base}/aets/{ae}/rs/studies'
        params = {'0020000D': study_uid, 'limit': '1'}
    else:
        path = f'{base}/aets/{ae}/rs/patients'
        params = {'00100020': patient_id, 'limit': '1'}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5, read=10)) as client:
            resp = await client.get(path, params=params)
    except httpx.HTTPError as exc:
        log.warning('weasis archive authz check failed: %s', exc)
        return False
    if resp.status_code >= 300:
        return False
    if resp.status_code == 204 or not resp.content:
        return False
    return bool(resp.json())


def _launch_url(study_uids, patient_id=''):
    """Build the connector launch URL.

    studyUID may repeat for multi-study launches; patientID launches the
    patient tab (no study selected yet).
    """
    base = str(config.get('weasis_launch_url', 'http://localhost:8082/weasis-pacs-connector')).rstrip('/')
    url = f'{base}/weasis?'
    params = []
    if patient_id:
        params.append(f'patientID={patient_id}')
    params.extend(f'studyUID={uid}' for uid in study_uids)
    url += '&'.join(params)
    url += '&cdb'
    return url


class WeasisLaunch(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        if not _weasis_enabled():
            return not_found('Weasis launch is disabled')

        study_uid = (request.query_params.get('studyUID') or '').strip()
        patient_id = (request.query_params.get('patientID') or '').strip()

        if not study_uid and not patient_id:
            from api.response import validation_error
            return validation_error('studyUID or patientID is required')

        if proxy_enabled():
            # Archive is the store of truth in proxy mode (see above).
            ok = await _archive_authorized(study_uid=study_uid, patient_id=patient_id)
        else:
            # Authz gate (local mode): the requesting user must be able to
            # see at least one file row for the study (or any study of the
            # patient). The files table is the tenancy boundary — same check
            # the DICOMweb surface relies on.
            async with get_conn() as conn:
                if study_uid:
                    ok = await conn.fetchval(
                        "SELECT EXISTS ("
                        "  SELECT 1 FROM files f"
                        "  JOIN series ser ON ser.id = f.series_id"
                        "  JOIN studies s ON s.id = ser.study_id"
                        "  WHERE s.study_instance_uid = $1 AND f.deleted = false"
                        ")", study_uid)
                else:
                    ok = await conn.fetchval(
                        "SELECT EXISTS ("
                        "  SELECT 1 FROM files f"
                        "  JOIN patients p ON p.id = f.patient_id"
                        "  WHERE p.patient_id = $1 AND f.deleted = false"
                        ")", patient_id)

        if not ok:
            return not_found('Study or patient not found')

        study_uids = [study_uid] if study_uid else []
        target = _launch_url(study_uids, patient_id=patient_id if not study_uid else '')
        log.info('weasis launch studyUID=%s patientID=%s -> %s', study_uid, patient_id, target)
        return RedirectResponse(target, status_code=302)


class WeasisStatus(HTTPEndpoint):
    """Status probe so UI launch buttons render only when the connector
    integration is enabled (ADR-028) — no launch side effects."""

    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        return ok({
            'enabled': _weasis_enabled(),
            'launch_url': str(config.get('weasis_launch_url', '')).rstrip('/'),
        })