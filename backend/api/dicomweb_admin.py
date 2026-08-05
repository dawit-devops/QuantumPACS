from starlette.endpoints import HTTPEndpoint
from datetime import timedelta

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok
from api.dicomweb import VALID_MODALITIES
from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)


def _get_qido_search_params():
    return [
        {'name': 'PatientID', 'type': 'string', 'description': 'Patient identifier'},
        {'name': 'PatientName', 'type': 'string', 'description': 'Patient name (exact or wildcard)'},
        {'name': 'AccessionNumber', 'type': 'string', 'description': 'Study accession number'},
        {'name': 'StudyInstanceUID', 'type': 'string', 'description': 'Study instance UID'},
        {'name': 'limit', 'type': 'integer', 'description': 'Max results (default 100)'},
        {'name': 'offset', 'type': 'integer', 'description': 'Result offset'},
    ]


def _get_wado_features():
    return {
        'retrieve_study': True,
        'retrieve_series': True,
        'retrieve_instance': True,
        'retrieve_metadata': False,
        'retrieve_bulkdata': False,
        'transfer_syntax': 'as_stored',
        'accept_header': 'multipart/related; type=application/dicom',
    }


class DicomWebAdminHandler(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        return ok({
            'qido': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies', 'method': 'GET', 'description': 'Search studies'},
                    {'path': '/dicomweb/studies/{study_uid}/series', 'method': 'GET', 'description': 'List series'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}/instances', 'method': 'GET', 'description': 'List instances'},
                ],
                'search_params': _get_qido_search_params(),
                'response_format': 'application/dicom+json',
                'pagination': 'limit/offset with X-Total-Count header',
            },
            'wado': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies/{study_uid}', 'method': 'GET', 'description': 'Retrieve study'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}', 'method': 'GET', 'description': 'Retrieve series'},
                    {'path': '/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}', 'method': 'GET', 'description': 'Retrieve instance'},
                    {'path': '/wado', 'method': 'GET', 'description': 'WADO-URI retrieval'},
                ],
                'features': _get_wado_features(),
            },
            'stow': {
                'enabled': True,
                'endpoints': [
                    {'path': '/dicomweb/studies', 'method': 'POST', 'description': 'Store instances'},
                ],
                'content_type': 'multipart/related; type=application/dicom',
                'modality_validation': True,
                'valid_modalities_count': len(VALID_MODALITIES),
            },
            'modalities': sorted(VALID_MODALITIES),
            'missing_features': [
                'Study metadata (GET /studies/{uid}/metadata)',
                'Series metadata (GET .../series/{uid}/metadata)',
                'Instance metadata (GET .../instances/{uid}/metadata)',
                'Frame retrieval (GET .../instances/{uid}/frames/{frames})',
                'Bulk data URI support',
                'Transfer syntax negotiation',
            ],
        })


class DicomWebMetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.DICOMWEB_READ)
    async def get(self, request):
        async with get_conn() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM files WHERE created > now() - $1::interval",
                timedelta(hours=24)
            )
        return ok({
            'period': '24h',
            'files_stored': total or 0,
            'metrics_note': 'Dedicated DICOMweb request logging not yet implemented',
        })
