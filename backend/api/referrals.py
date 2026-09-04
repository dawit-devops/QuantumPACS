"""RIS Referral Tracking API (CC-05).

Coordinators track referrals from an ordering provider to a specialist.
GET lists referrals (status/patient filters); POST creates a new referral;
PATCH /{id} advances status (pending -> accepted -> completed / cancelled)
and updates notes.
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found
from api.validate import parse_body
from api.schemas.ris_referrals import CreateReferralRequest, UpdateReferralRequest
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class ReferralsHandler(HTTPEndpoint):
    """CC-05: GET /ris/referrals (list) and POST /ris/referrals (create)."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            from db.ris_referrals import Referrals
            rows = await Referrals(conn).list(
                tenant, status=status, patient_id=patient_id)
        return ok({'data': rows})

    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreateReferralRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_referrals import Referrals
            row = await Referrals(conn).create(
                patient_id=body.patient_id,
                from_provider=body.from_provider,
                to_specialist=body.to_specialist,
                specialty=body.specialty,
                order_id=body.order_id,
                report_id=body.report_id,
                notes=body.notes,
                by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='referral.created',
                actor_id=request.user.id,
                resource_type='ris_referrals',
                resource_id=row['id'],
                details={'patient_id': body.patient_id,
                         'to_specialist': body.to_specialist},
                tenant=tenant,
            )
        return created({'data': row})


class ReferralDetailHandler(HTTPEndpoint):
    """CC-05: PATCH /ris/referrals/{id} — advance status + notes."""

    @requires_permission(Permission.PATIENT_WRITE)
    async def patch(self, request):
        referral_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        body = await parse_body(UpdateReferralRequest, request)
        async with get_conn() as conn:
            from db.ris_referrals import Referrals
            rf = Referrals(conn)
            existing = await rf.get(referral_id, tenant)
            if not existing:
                return not_found('Referral not found')
            await rf.update(
                referral_id=referral_id,
                status=body.status,
                notes=body.notes,
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='referral.updated',
                actor_id=request.user.id,
                resource_type='ris_referrals',
                resource_id=referral_id,
                details={'status': body.status},
                tenant=tenant,
            )
        return ok({'status': 'updated'})