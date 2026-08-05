from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, not_found
from api.utils import get_id
from db.conn import get_conn
from db.patient import Patient
from services.interfaces import MetadataService


async def get_patient_by_id(request):
    patient_id = get_id(request)
    services = getattr(request.state, 'services', None)
    if services is not None:
        try:
            metadata = services.get(MetadataService)
            result = await metadata.get_patient(str(patient_id))
            if result:
                return result
        except KeyError:
            pass
    async with get_conn() as conn:
        return await Patient(conn).get_extra(patient_id)


class PatientHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        data = await get_patient_by_id(request)
        if not data:
            return not_found()
        return ok(data)
