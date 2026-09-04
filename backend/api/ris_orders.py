"""RIS order intake API (E-RIS-03) — create/list orders and transition status.

Permission-gated with ORDER_WRITE (create/transition) and ORDER_READ (list/
detail). Status transitions delegate to the order lifecycle service so the
VALID_TRANSITIONS state machine and audit stay in one place.
"""
from datetime import date, datetime, time
from uuid import UUID

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, created, not_found, api_error
from api.validate import parse_body
from api.schemas.ris_orders import CreateOrderRequest, OrderStatusUpdateRequest
from db.audit_log import AuditLog
from db.conn import get_conn
from db.ris_appointments import RisAppointments
from db.ris_orders import RisOrders, RisOrderProcedures
from services.order_lifecycle.service import OrderLifecycleService, InvalidTransitionError


def _row_dict(row):
    """Serialize a DB row for JSON responses — date/time/uuid become strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, UUID)):
            d[k] = str(v)
    return d


class RisOrdersHandler(HTTPEndpoint):
    @requires_permission(Permission.ORDER_WRITE)
    async def post(self, request):
        body = await parse_body(CreateOrderRequest, request)
        async with get_conn() as conn:
            orders = RisOrders(conn)
            procedures = RisOrderProcedures(conn)
            try:
                order = await orders.create(body.model_dump())
            except Exception:
                # Unique (tenant_id, accession_number) violation → 409 so
                # duplicate HL7 ORM deliveries surface instead of 500ing.
                from asyncpg import UniqueViolationError
                exc_info = __import__('sys').exc_info()[1]
                if isinstance(exc_info, UniqueViolationError):
                    return api_error(
                        'CONFLICT',
                        f"Order with accession {body.accession_number} already exists",
                        status=409,
                    )
                raise
            created_procedures = []
            for p in body.procedures:
                proc = await procedures.create(order['id'], p.model_dump())
                created_procedures.append(_row_dict(proc))
        return created({'data': {
            'order': _row_dict(order),
            'procedures': created_procedures,
        }})

    @requires_permission(Permission.ORDER_READ)
    async def get(self, request):
        params = request.query_params
        try:
            page = max(int(params.get('page', 1)), 1)
            per_page = min(max(int(params.get('per_page', 25)), 1), 100)
        except ValueError:
            return api_error('VALIDATION', 'page/per_page must be integers', status=422)
        offset = (page - 1) * per_page
        # S-4: the referring-MD view is identity-scoped. A physician caller
        # sees only orders attributed to their own identity (username) —
        # the free-text probe is ignored, so one MD cannot enumerate
        # another's orders by name. Staff keep the probe (their workflow).
        referring_md = params.get('referring_md') or None
        if request.user.role_slug == 'physician':
            referring_md = request.user.username or None
        async with get_conn() as conn:
            repo = RisOrders(conn)
            rows = await repo.list(
                limit=per_page, offset=offset,
                status=params.get('status') or None,
                patient_id=params.get('patient_id') or None,
                search=params.get('search') or None,
                referring_md=referring_md,
                date_from=params.get('date_from') or None,
                date_to=params.get('date_to') or None,
            )
            total = await repo.count(
                status=params.get('status') or None,
                patient_id=params.get('patient_id') or None,
                search=params.get('search') or None,
                referring_md=referring_md,
                date_from=params.get('date_from') or None,
                date_to=params.get('date_to') or None,
            ) or 0
        return ok({
            'data': [_row_dict(r) for r in rows],
            'total': total,
            'page': page,
            'per_page': per_page,
        })


class RisOrderHandler(HTTPEndpoint):
    @requires_permission(Permission.ORDER_READ)
    async def get(self, request):
        order_id = request.path_params['id']
        async with get_conn() as conn:
            order = await RisOrders(conn).get(order_id)
            if not order:
                return not_found('Order not found')
            procs = await RisOrderProcedures(conn).list_for_order(order_id)
            # S4-02: scheduling state ships with the detail payload so the
            # coordinator sees the full picture without a second round-trip.
            appts = await RisAppointments(conn).list_for_order(order_id)
        return ok({'data': {
            'order': _row_dict(order),
            'procedures': [_row_dict(p) for p in procs],
            'appointments': [_row_dict(a) for a in appts],
        }})


class RisOrderHistoryHandler(HTTPEndpoint):
    @requires_permission(Permission.ORDER_READ)
    async def get(self, request):
        order_id = request.path_params['id']
        async with get_conn() as conn:
            order = await RisOrders(conn).get(order_id)
            if not order:
                return not_found('Order not found')
            # Audit timeline for this order: status transitions, bookings,
            # cancellations — newest first from the log, reversed to
            # chronological for the UI.
            rows = await AuditLog(conn).query(
                resource_id=order_id, limit=200)
        events = []
        for r in reversed(rows):
            # B-3: expose the structured audit detail (from/to/reason,
            # overrode lists, slot) — the UI renders these fields; a
            # stringified description loses the shape.
            events.append({
                'event': r['event_type'],
                'actor': r['actor'],
                'timestamp': r['created_at'],
                'details': r['payload'].get('detail'),
                'resource_type': r['resource_type'],
                'resource_id': r['resource_id'],
            })
        return ok({'data': events})


class RisOrderStatusHandler(HTTPEndpoint):
    @requires_permission(Permission.ORDER_WRITE)
    async def put(self, request):
        body = await parse_body(OrderStatusUpdateRequest, request)
        order_id = request.path_params['id']
        actor_id = str(getattr(request.user, 'id', ''))
        async with get_conn() as conn:
            try:
                order = await OrderLifecycleService(conn).transition(
                    order_id, body.status, actor_id, body.reason,
                )
            except InvalidTransitionError as e:
                return api_error('INVALID_TRANSITION', str(e), status=422)
            if not order:
                return not_found('Order not found')
            procs = await RisOrderProcedures(conn).list_for_order(order_id)
        return ok({'data': {
            'order': _row_dict(order),
            'procedures': [_row_dict(p) for p in procs],
        }})