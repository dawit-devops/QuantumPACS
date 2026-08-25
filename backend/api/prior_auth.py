"""RIS Prior Authorization API (R2-01).

Submit / list prior-auth requests and apply payer decisions (approve/deny).
Decisions sync ris_orders.prior_auth_status so the existing scheduling-gate
check (engine.py C-7) blocks REQUIRED/PENDING/DENIED/EXPIRED orders. Expiry
is a DB-layer sweep (expire_overdue) called by a background loop; the
expiring-soon list feeds the <= 7d alert (R2-01-07).
"""

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, validation_error
from api.validate import parse_body
from api.schemas.ris_prior_auth import (
    SubmitPriorAuthRequest,
    PriorAuthDecisionRequest,
    OverridePriorAuthRequest,
)
from db.conn import get_conn
from api.tenant_middleware import effective_tenant


class PriorAuthHandler(HTTPEndpoint):
    """R2-01-02: GET /ris/prior-auth (list) and POST /ris/prior-auth (submit)."""

    @requires_permission(Permission.PRIOR_AUTH_READ)
    async def get(self, request):
        tenant = effective_tenant(request) or 'default'
        status = request.query_params.get('status')
        expiring_soon = request.query_params.get('expiring_soon', '') == '1'
        days = request.query_params.get('days', '7')
        try:
            days = max(1, min(30, int(days)))
        except (TypeError, ValueError):
            days = 7
        async with get_conn() as conn:
            from db.ris_prior_auth import PriorAuth
            if expiring_soon:
                rows = await PriorAuth(conn).list_expiring_soon(days, tenant)
                return ok({'data': [dict(r) for r in rows], 'total': len(rows)})
            rows, total = await PriorAuth(conn).list(tenant, status=status)
        return ok({'data': rows, 'total': total})

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        body = await parse_body(SubmitPriorAuthRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_prior_auth import PriorAuth
            await PriorAuth(conn).create_request(
                order_id=body.order_id,
                procedure_code=body.procedure_code,
                payer_id=body.payer_id,
                payer_name=body.payer_name,
                requested_by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='prior_auth.submitted',
                actor_id=request.user.id,
                resource_type='ris_prior_auth_requests',
                resource_id=body.order_id,
                tenant=tenant,
            )
        return created({'status': 'REQUIRED', 'order_id': body.order_id})


class PriorAuthDecisionHandler(HTTPEndpoint):
    """R2-01-02: POST /ris/prior-auth/{id}/decision — approve|deny."""

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        request_id = request.path_params['id']
        body = await parse_body(PriorAuthDecisionRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_prior_auth import PriorAuth
            pa = await PriorAuth(conn).get(request_id, tenant)
            if not pa:
                return not_found('Prior-auth request not found')
            if pa['status'] != 'PENDING':
                return validation_error(
                    f'Only PENDING requests can be decided (current: {pa["status"]})')
            if body.action == 'approve':
                result = await PriorAuth(conn).approve(
                    request_id=request_id,
                    auth_number=body.auth_number or '',
                    approved_units=body.approved_units,
                    approved_date=body.approved_date,
                    expiry_date=body.expiry_date,
                    decided_by=str(request.user.id),
                    tenant_id=tenant,
                )
                final = 'APPROVED'
            else:
                result = await PriorAuth(conn).deny(
                    request_id=request_id,
                    denial_reason=body.denial_reason or '',
                    decided_by=str(request.user.id),
                    tenant_id=tenant,
                )
                final = 'DENIED'
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                # final is already 'APPROVED'/'DENIED' — lowercasing yields
                # the canonical event suffix directly (approved/denied).
                event_type=f'prior_auth.{final.lower()}',
                actor_id=request.user.id,
                resource_type='ris_prior_auth_requests',
                resource_id=request_id,
                details={'order_id': (result or {}).get('order_id')},
                tenant=tenant,
            )
        return ok({'id': request_id, 'status': final})


class PriorAuthSubmitForReviewHandler(HTTPEndpoint):
    """CS1/CC-11: POST /ris/prior-auth/{id}/submit — REQUIRED → PENDING.

    Wires the previously orphaned PriorAuth.submit_for_review(); without it
    API-created requests stayed REQUIRED and could never reach the decision
    endpoint (which demands PENDING)."""

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        from db.ris_prior_auth import PriorAuth
        request_id = request.path_params['id']
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            pa = await PriorAuth(conn).get(request_id, tenant)
            if not pa:
                return not_found('Prior-auth request not found')
            if pa['status'] != 'REQUIRED':
                return validation_error(
                    f'Only REQUIRED requests can be submitted for review '
                    f'(current: {pa["status"]})')
            await PriorAuth(conn).submit_for_review(
                request_id=request_id, tenant_id=tenant)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='prior_auth.review_requested',
                actor_id=request.user.id,
                resource_type='ris_prior_auth_requests',
                resource_id=str(request_id),
                details={'order_id': (pa or {}).get('order_id')},
                tenant=tenant,
            )
        return ok({'data': {'id': str(request_id), 'status': 'PENDING'}})


class PriorAuthOverrideHandler(HTTPEndpoint):
    """CS1/CC-11: POST /ris/prior-auth/{id}/override — flip an unapproved
    request to NOT_REQUIRED with a mandatory reason (audited)."""

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        from db.ris_prior_auth import PriorAuth
        request_id = request.path_params['id']
        body = await parse_body(OverridePriorAuthRequest, request)
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            pa = await PriorAuth(conn).get(request_id, tenant)
            if not pa:
                return not_found('Prior-auth request not found')
            if pa['status'] in ('APPROVED', 'NOT_REQUIRED'):
                return validation_error(
                    f'{pa["status"]} requests cannot be overridden')
            result = await PriorAuth(conn).override(
                request_id=request_id,
                overridden_by=str(request.user.id),
                tenant_id=tenant,
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='prior_auth.overridden',
                actor_id=request.user.id,
                resource_type='ris_prior_auth_requests',
                resource_id=str(request_id),
                details={'reason': body.reason,
                         'previous_status': pa['status'],
                         'order_id': (result or {}).get('order_id')},
                tenant=tenant,
            )
        return ok({'data': {'id': str(request_id),
                            'status': 'NOT_REQUIRED'}})


class PriorAuthExpireHandler(HTTPEndpoint):
    """R2-01-02: POST /ris/prior-auth/expire — run the expiry sweep.

    Normally driven by a background loop; exposed for operator/manual runs
    and the E2E path.
    """

    @requires_permission(Permission.PRIOR_AUTH_WRITE)
    async def post(self, request):
        tenant = effective_tenant(request) or 'default'
        async with get_conn() as conn:
            from db.ris_prior_auth import PriorAuth
            expired = await PriorAuth(conn).expire_overdue(tenant)
        return ok({'expired': len(expired)})
