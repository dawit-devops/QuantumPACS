"""MPPS event audit read path (M-4, S6-08).

ris_mpps_events is written by the MPPS consumer but had no API surface —
modalities could push status into the system with no way to inspect the
trail. WORKLIST_READ holders (front desk, modality admin) can query the
event history for an accession number.
"""
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, validation_error
from db.conn import get_conn
from db.ris_mpps import RisMppsEvents


class MppsEventsHandler(HTTPEndpoint):
    @requires_permission(Permission.WORKLIST_READ)
    async def get(self, request):
        accession = request.query_params.get('accession', '')
        if not accession:
            return validation_error('accession query parameter is required')
        try:
            limit = int(request.query_params.get('limit', '50'))
        except (TypeError, ValueError):
            return validation_error('Invalid limit parameter')
        if limit < 1 or limit > 200:
            return validation_error('limit must be between 1 and 200')

        async with get_conn() as conn:
            events = await RisMppsEvents(conn).list_by_accession(
                accession, limit=limit)
        return ok({'data': events, 'total': len(events)})
