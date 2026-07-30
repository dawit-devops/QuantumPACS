import time

from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import ok, api_error
from api.schemas.hl7_admin import Hl7ConfigUpdate
from api.validate import parse_body
from config import config
from db.conn import get_conn
from db.hl7_message import Hl7Message
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
