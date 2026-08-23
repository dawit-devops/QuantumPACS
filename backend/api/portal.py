"""R19 Hospital Staff Portal endpoints.

Patient data is only ever reachable through patient_staff_scope for the
requesting user (minimum necessary, HIPAA). Out-of-scope lookups return
`data: None` instead of a 403 wall — scope absence is indistinguishable
from "no such patient", so staff cannot enumerate or probe other patients.
"""
from starlette.endpoints import HTTPEndpoint

from api.notify import notify_role
from api.permissions import Permission
from api.rbac import requires_permission
from api.response import created, not_found, ok, validation_error
from api.schemas.portal import (
    CreateFollowUpRequest,
    CreateScopeRequest,
    UpdateFollowUpRequest,
)
from api.validate import parse_body
from db.audit_log import AuditLog
from db.conn import get_conn
from db.portal import Portal
from log import request_id_var
from api.tenant_middleware import effective_tenant


class PortalScopeHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await Portal(conn).list_scope(request.user.id)
        return ok({'data': rows})

    @requires_permission(Permission.FOLLOW_UP_WRITE)
    async def post(self, request):
        # Scope creation is a staff-side write: FOLLOW_UP_WRITE is the
        # portal's write grant and no patient role carries it. PORTAL_READ
        # alone (the patient role's grant) must never be able to attach a
        # scope to an arbitrary patient (R3-01).
        body = await parse_body(CreateScopeRequest, request)
        async with get_conn() as conn:
            portal = Portal(conn)
            if not await portal.patient_exists(body.patient_id):
                return not_found('Patient not found')
            existing = await portal.get_scope(body.patient_id, request.user.id)
            if existing:
                # R5-14: the idempotent re-attach path is a state change from
                # the caller's perspective — an audit row proves the scope was
                # (re)confirmed, not just created.
                await AuditLog(conn).log_event(
                    event_type='portal.scope_exists',
                    actor_id=request.user.id,
                    resource_type='patient_scope',
                    resource_id=existing['id'],
                    details={
                        'patient_id': body.patient_id,
                        'scope_type': existing['scope_type'],
                        'existing': True,
                    },
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
                return ok({
                    'data': {
                        'id': existing['id'],
                        'scope_type': existing['scope_type'],
                        'existing': True,
                    }
                })
            row = await portal.create_scope(
                body.patient_id, request.user.id, body.scope_type,
            )
            if row is None:
                existing = await portal.get_scope(body.patient_id, request.user.id)
                await AuditLog(conn).log_event(
                    event_type='portal.scope_exists',
                    actor_id=request.user.id,
                    resource_type='patient_scope',
                    resource_id=existing['id'],
                    details={
                        'patient_id': body.patient_id,
                        'scope_type': existing['scope_type'],
                        'existing': True,
                    },
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
                return ok({
                    'data': {
                        'id': existing['id'],
                        'scope_type': existing['scope_type'],
                        'existing': True,
                    }
                })
            await AuditLog(conn).log_event(
                event_type='portal.scope_added',
                actor_id=request.user.id,
                resource_type='patient_scope',
                resource_id=row['id'],
                details={
                    'patient_id': body.patient_id,
                    'scope_type': row['scope_type'],
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': {'id': row['id'], 'scope_type': row['scope_type']}})

    @requires_permission(Permission.PORTAL_READ)
    async def delete(self, request):
        scope_id = request.path_params['id']
        async with get_conn() as conn:
            row = await Portal(conn).delete_scope(scope_id, request.user.id)
            if not row:
                return not_found('Scope entry not found')
            await AuditLog(conn).log_event(
                event_type='portal.scope_removed',
                actor_id=request.user.id,
                resource_type='patient_scope',
                resource_id=row['id'],
                details={'patient_id': row['patient_id']},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class PortalPatientSearchHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        q = request.query_params.get('q', '')
        query = q.strip()
        if len(query) < 2:
            return ok({'data': []})
        async with get_conn() as conn:
            rows = await Portal(conn).search_patients(request.user.id, query)
            await AuditLog(conn).log_event(
                event_type='portal.patient_search',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=None,
                # No PHI in details — query string and result count only.
                details={'query': query, 'result_count': len(rows)},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': rows})


class PortalPatientHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        patient_id = request.path_params['patient_id']
        async with get_conn() as conn:
            portal = Portal(conn)
            scope = await portal.get_scope(patient_id, request.user.id)
            if not scope:
                await AuditLog(conn).log_event(
                    event_type='portal.patient_view',
                    actor_id=request.user.id,
                    resource_type='patient',
                    resource_id=patient_id,
                    details={'scoped': False, 'scope_type': None},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
                return ok({'data': None})
            demo = await portal.get_demographics(patient_id)
            orders = await portal.list_orders(patient_id)
            reports = await portal.list_final_reports(patient_id)
            # E1: scoped but no consent -> the empty view is consent-gated;
            # audit it so HIM can distinguish gating from no-data.
            if demo is None and await portal.consent_granted(patient_id) is None \
                    and scope:
                await AuditLog(conn).log_event(
                    event_type='portal.consent_blocked',
                    actor_id=request.user.id,
                    resource_type='patient',
                    resource_id=patient_id,
                    details={'patient_id': patient_id},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
            await AuditLog(conn).log_event(
                event_type='portal.patient_view',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=patient_id,
                details={
                    'scoped': True,
                    'scope_type': scope['scope_type'],
                    'order_count': len(orders),
                    'report_count': len(reports),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({
            'data': {
                'patient': dict(demo) if demo else None,
                'orders': orders,
                'reports': reports,
            }
        })


class PortalReportHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        patient_id = request.path_params['patient_id']
        report_id = request.path_params['report_id']
        async with get_conn() as conn:
            portal = Portal(conn)
            scope = await portal.get_scope(patient_id, request.user.id)
            if not scope:
                await AuditLog(conn).log_event(
                    event_type='portal.report_view',
                    actor_id=request.user.id,
                    resource_type='report',
                    resource_id=report_id,
                    details={'scoped': False, 'scope_type': None},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
                return ok({'data': None})
            row = await portal.get_final_report(patient_id, report_id)
            if not row:
                # A4: a scoped patient hitting a HIM-held report is a
                # blocked patient-visible access — audit it before the 404.
                if await portal.release_blocked(patient_id, report_id):
                    await AuditLog(conn).log_event(
                        event_type='portal.report_hold_blocked',
                        actor_id=request.user.id,
                        resource_type='report',
                        resource_id=report_id,
                        details={'patient_id': patient_id},
                        tenant=effective_tenant(request),
                        request_id=request_id_var.get(),
                    )
                return not_found('Report not found')
            await AuditLog(conn).log_event(
                event_type='portal.report_view',
                actor_id=request.user.id,
                resource_type='report',
                resource_id=report_id,
                details={'scoped': True, 'scope_type': scope['scope_type']},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': row})


class PortalOrdersHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        patient_id = request.path_params['patient_id']
        async with get_conn() as conn:
            portal = Portal(conn)
            scope = await portal.get_scope(patient_id, request.user.id)
            if not scope:
                await AuditLog(conn).log_event(
                    event_type='portal.orders_view',
                    actor_id=request.user.id,
                    resource_type='patient',
                    resource_id=patient_id,
                    details={'scoped': False, 'scope_type': None},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
                return ok({'data': []})
            orders = await portal.list_orders(patient_id)
            # E1: a scoped patient whose consent was not (yet) granted sees
            # an empty list — audit the blocked access distinctly so HIM can
            # tell consent-gating from a genuinely absent order set.
            if scope and not orders and not await portal.consent_granted(patient_id):
                await AuditLog(conn).log_event(
                    event_type='portal.consent_blocked',
                    actor_id=request.user.id,
                    resource_type='patient',
                    resource_id=patient_id,
                    details={'patient_id': patient_id},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
            await AuditLog(conn).log_event(
                event_type='portal.orders_view',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=patient_id,
                details={
                    'scoped': True,
                    'scope_type': scope['scope_type'],
                    'order_count': len(orders),
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': orders})


class PortalFollowUpHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        async with get_conn() as conn:
            rows = await Portal(conn).list_follow_ups(request.user.id, status)
        return ok({'data': rows})

    @requires_permission(Permission.FOLLOW_UP_WRITE)
    async def post(self, request):
        body = await parse_body(CreateFollowUpRequest, request)
        async with get_conn() as conn:
            portal = Portal(conn)
            # Follow-ups reference a patient identity — the one portal write
            # path that touches patient data must respect the scope boundary
            # like every read path (R3-02). 404 keeps the "no such patient"
            # ambiguity of the read paths, so staff cannot probe.
            if not await portal.get_scope(body.patient_id, request.user.id):
                return not_found('Patient not found')
            if not await portal.follow_up_targets_valid(
                body.patient_id, body.report_id, body.exam_id,
            ):
                return validation_error(
                    'Report or exam does not belong to the patient'
                )
            row = await portal.create_follow_up(request.user.id, body)
            await AuditLog(conn).log_event(
                event_type='portal.follow_up_created',
                actor_id=request.user.id,
                resource_type='follow_up_request',
                resource_id=row['id'],
                details={
                    'patient_id': body.patient_id,
                    'priority': body.priority,
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
            await notify_role(
                conn,
                'radiologist',
                'portal.follow_up_request',
                'Follow-up requested',
                f'{body.reason} — priority {body.priority}',
                '/reading',
            )
        return created({'data': {'id': row['id']}})


class PortalFollowUpStatusHandler(HTTPEndpoint):
    @requires_permission(Permission.PORTAL_READ)
    async def put(self, request):
        follow_up_id = request.path_params['id']
        body = await parse_body(UpdateFollowUpRequest, request)
        async with get_conn() as conn:
            row = await Portal(conn).update_follow_up_status(
                follow_up_id, request.user.id, body.status,
            )
            if not row:
                return not_found('Follow-up not found')
            if body.status == 'cancelled':
                await AuditLog(conn).log_event(
                    event_type='portal.follow_up_cancelled',
                    actor_id=request.user.id,
                    resource_type='follow_up_request',
                    resource_id=follow_up_id,
                    details={'status': body.status},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
        return ok({})
