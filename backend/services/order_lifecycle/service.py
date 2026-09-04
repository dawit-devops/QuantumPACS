"""Order lifecycle state machine (E-RIS-03) — valid transitions + audit.

Spec §4.3: VALID_TRANSITIONS enforced by the service layer so every status
change is validated once, audited, and side-effect hooks stay centralized.
"""

VALID_TRANSITIONS = {
    'ORDERED':     ['SCHEDULED', 'CANCELLED'],
    'SCHEDULED':   ['ARRIVED', 'CANCELLED'],
    'ARRIVED':     ['IN_PROGRESS', 'CANCELLED'],
    'IN_PROGRESS': ['COMPLETED', 'CANCELLED'],
    'COMPLETED':   ['READ'],
    'READ':        ['SIGNED'],
    'SIGNED':      [],  # terminal
    'CANCELLED':   ['ORDERED'],  # can re-order
}


class InvalidTransitionError(Exception):
    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(
            f"Invalid order transition {current} -> {requested}"
        )


class OrderLifecycleService:
    """State machine for order status transitions with guards + audit."""

    def __init__(self, conn):
        self.conn = conn

    async def transition(self, order_id, new_status, actor_id, reason=None):
        from db.ris_orders import RisOrders
        from db.audit_log import AuditLog

        orders = RisOrders(self.conn)
        order = await orders.get(order_id)
        if not order:
            return None
        current = order['status']
        if new_status not in VALID_TRANSITIONS.get(current, []):
            raise InvalidTransitionError(current, new_status)

        updated = await orders.update_status(order_id, new_status)
        await AuditLog(self.conn).log_event(
            event_type='ORDER_STATUS_TRANSITION',
            actor_id=actor_id,
            resource_type='ris_orders',
            resource_id=order_id,
            details={'from': current, 'to': new_status, 'reason': reason},
        )
        return updated