import time
from datetime import date, datetime
from uuid import UUID

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, api_error
from api.schemas.hl7_admin import Hl7ConfigUpdate
from api.validate import parse_body
from config import config
from db.conn import get_conn
from db.hl7_message import Hl7Message
from db.ris_hl7 import RisHl7Messages, RisInterfaceEndpoints
from log import get_logger

log = get_logger(__name__)


class Hl7MessagesHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        limit = int(request.query_params.get('limit', '50'))
        offset = int(request.query_params.get('offset', '0'))
        message_type = request.query_params.get('message_type', '')
        parse_status = request.query_params.get('parse_status', '')
        patient_id = request.query_params.get('patient_id', '')
        sending_facility = request.query_params.get('sending_facility', '')

        async with get_conn() as conn:
            msgs, total = await Hl7Message(conn).get_messages(
                limit=limit, offset=offset,
                message_type=message_type, parse_status=parse_status,
                patient_id=patient_id, sending_facility=sending_facility,
            )
        return ok({'messages': msgs, 'total': total, 'limit': limit, 'offset': offset})


class Hl7MessageHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        msg_id = request.path_params['id']
        async with get_conn() as conn:
            hm = Hl7Message(conn)
            msg = await hm.get_by_id(msg_id)
            if not msg:
                return api_error('NOT_FOUND', 'Message not found', status=404)
            errors = await hm.get_errors_for_message(msg_id)
            if msg.get('parsed_fields') and isinstance(msg['parsed_fields'], str):
                import json
                try:
                    msg['parsed_fields'] = json.loads(msg['parsed_fields'])
                except (json.JSONDecodeError, TypeError):
                    pass
        msg['errors'] = errors
        return ok(msg)


class Hl7MetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        period_map = {'1h': '1 hour', '24h': '24 hours', '7d': '7 days', '30d': '30 days'}
        period = period_map.get(request.query_params.get('period', '24h'), '24 hours')
        async with get_conn() as conn:
            metrics = await Hl7Message(conn).get_metrics(period)
        return ok({'period': request.query_params.get('period', '24h'), **metrics})


class Hl7ConfigHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        return ok({
            'mllp_host': '',
            'mllp_port': int(config.get('hl7_mllp_port', '12579')),
            'tls_enabled': bool(config.get('hl7_mllp_tls_cert')),
            'allowed_ips': [s.strip() for s in config.get('hl7_mllp_allowed_ips', '').split(',') if s.strip()],
        })

    @requires_permission(Permission.HL7_WRITE)
    async def put(self, request):
        data = await parse_body(Hl7ConfigUpdate, request)
        updates = {}
        if data.allowed_ips is not None:
            updates['hl7_mllp_allowed_ips'] = ','.join(data.allowed_ips)
        if data.mllp_port is not None:
            updates['hl7_mllp_port'] = str(data.mllp_port)
        if updates:
            import yaml
            try:
                with open('config.local.yaml') as f:
                    local = yaml.safe_load(f) or {}
            except Exception:
                local = {}
            local.update(updates)
            with open('config.local.yaml', 'w') as f:
                yaml.dump(local, f)
        return ok({'updated': list(updates.keys())})


class Hl7StatusHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        import socket
        port = int(config.get('hl7_mllp_port', '12579'))
        host = config.get('hl7_mllp_host', '')
        start = time.monotonic()
        try:
            s = socket.create_connection((host or '127.0.0.1', port), timeout=3)
            s.close()
            reachable = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            reachable = False
        elapsed = round((time.monotonic() - start) * 1000)
        return ok({
            'listening': reachable,
            'host': host or '0.0.0.0',
            'port': port,
            'response_time_ms': elapsed,
        })


# --- S3-15 Interface dashboard API (E-RIS-02 #4, RIS-AC-P06-02) ----------
# Reads the engine's own tables (ris_interface_endpoints / ris_hl7_messages)
# rather than the legacy hl7_messages admin views above. Endpoints are the
# registered interfaces; exceptions is the FAILED queue backing the UI.

_PERIODS = {'1h': '1 hour', '24h': '24 hours', '7d': '7 days', '30d': '30 days'}


def _require_uuid(value):
    """Validate the {id} path param is a UUID — repo queries inline it."""
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        return None


def _row_dict(row):
    """Serialize a DB row for JSON responses — uuid/date/datetime become strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (UUID, date, datetime)):
            d[k] = str(v)
    return d


class RisInterfacesHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        async with get_conn() as conn:
            endpoints = await RisInterfaceEndpoints(conn).list()
            counts = await RisHl7Messages(conn).count_by_endpoints(
                [e['id'] for e in endpoints],
            )
        interfaces = []
        for ep in endpoints:
            row = _row_dict(ep)
            # Expose only the interesting statuses; RECEIVED is implied by
            # the totals and would duplicate the counter row for every msg.
            row['status_counts'] = {
                st: n for st, n in counts.get(ep['id'], {}).items() if st != 'RECEIVED'
            }
            interfaces.append(row)
        return ok({'data': {'interfaces': interfaces, 'total': len(interfaces)}})


class RisInterfaceMessagesHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        endpoint_id = _require_uuid(request.path_params['id'])
        if endpoint_id is None:
            return api_error('INTERFACE_NOT_FOUND', 'Interface endpoint not found', status=404)
        limit = int(request.query_params.get('limit', '50'))
        offset = int(request.query_params.get('offset', '0'))
        async with get_conn() as conn:
            ep = await RisInterfaceEndpoints(conn).get(endpoint_id)
            if not ep:
                return api_error('INTERFACE_NOT_FOUND', 'Interface endpoint not found', status=404)
            msgs, total = await RisHl7Messages(conn).list_by_endpoint(
                endpoint_id, limit=limit, offset=offset,
            )
        return ok({'data': {
            'messages': [_row_dict(m) for m in msgs],
            'total': total, 'limit': limit, 'offset': offset,
        }})


class RisInterfaceMetricsHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        endpoint_id = _require_uuid(request.path_params['id'])
        if endpoint_id is None:
            return api_error('INTERFACE_NOT_FOUND', 'Interface endpoint not found', status=404)
        period_key = request.query_params.get('period', '24h')
        period = _PERIODS.get(period_key, '24 hours')
        async with get_conn() as conn:
            ep = await RisInterfaceEndpoints(conn).get(endpoint_id)
            if not ep:
                return api_error('INTERFACE_NOT_FOUND', 'Interface endpoint not found', status=404)
            metrics = await RisHl7Messages(conn).metrics_by_endpoint(endpoint_id, period)
        return ok({'data': {'endpoint_id': endpoint_id, 'period': period_key, **metrics}})


class RisInterfaceExceptionsHandler(HTTPEndpoint):
    @requires_permission(Permission.HL7_READ)
    async def get(self, request):
        limit = int(request.query_params.get('limit', '50'))
        async with get_conn() as conn:
            exceptions = await RisHl7Messages(conn).list_failed(limit)
        return ok({'data': {
            'exceptions': [_row_dict(m) for m in exceptions],
            'count': len(exceptions),
        }})
