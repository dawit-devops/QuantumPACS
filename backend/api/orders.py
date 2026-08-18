"""Orders (coordination) API — care_coordinator review P0-2.

Read-only list for ORDER_READ holders (care_coordinator, physician, ...). Write
actions (status updates, coordinator assignment) are future work and must gate
on ORDER_WRITE when shipped.
"""

from datetime import date, datetime, time
from uuid import UUID

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok
from db.conn import get_conn
from db.orders import Orders


def _row_dict(row):
    """Serialize a DB row for JSON responses — date/time/uuid become strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, UUID)):
            d[k] = str(v)
    return d


class OrdersHandler(HTTPEndpoint):
    @requires_permission(Permission.ORDER_READ)
    async def get(self, request):
        async with get_conn() as conn:
            rows = await Orders(conn).list_for_coordinator()
        return ok({'data': [_row_dict(r) for r in rows]})
