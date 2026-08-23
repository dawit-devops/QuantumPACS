"""RIS-REG-04 — portal kiosk self-check-in.

The kiosk has no login; the QR token IS the credential: an HMAC-signed,
expiring payload embedding tenant + appointment id. GET validates and
shows the visit summary (minimal PHI — display name only); POST flips
SCHEDULED -> ARRIVED and rejects repeats (409).
"""
import base64
import hashlib
import hmac
import json
import time

from starlette.endpoints import HTTPEndpoint

from api.response import api_error, not_found, ok
from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)


def _sign(payload: bytes) -> str:
    from config import config
    return hmac.new(config['secret'].encode(), payload,
                    hashlib.sha256).hexdigest()


def make_checkin_token(tenant, appointment_id, ttl_seconds=86400):
    body = base64.urlsafe_b64encode(json.dumps({
        't': tenant,
        'a': appointment_id,
        'e': int(time.time()) + ttl_seconds,
    }).encode()).decode().rstrip('=')
    return f'{body}.{_sign(body.encode())}'


def verify_checkin_token(token):
    """Constant-time signature check + expiry gate. None == reject."""
    body, _, sig = token.rpartition('.')
    if not body or not sig:
        return None
    if not hmac.compare_digest(sig, _sign(body.encode())):
        return None
    try:
        pad = '=' * (-len(body) % 4)
        data = json.loads(base64.urlsafe_b64decode(body + pad))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get('e', 0) < time.time():
        return None
    if not data.get('t') or not data.get('a'):
        return None
    return data


class PortalCheckInHandler(HTTPEndpoint):
    """GET/POST /ris/checkin/{token} — no auth middleware: the signed
    token is the bearer credential and it expires."""

    async def _claims(self, request):
        claims = verify_checkin_token(request.path_params['token'])
        if not claims:
            return None
        return claims

    async def get(self, request):
        claims = await self._claims(request)
        if not claims:
            return api_error('INVALID_TOKEN', 'Token invalid or expired',
                             status=403)
        async with get_conn() as conn:
            from db.ris_appointments import RisAppointments
            row = await RisAppointments(conn).get_for_checkin(
                claims['a'], claims['t'])
            if not row:
                return not_found('Appointment not found')
        # minimal PHI: display name + time + prep instructions. No MRN.
        return ok({'patient_name': row.get('patient_name'),
                   'start_time': row.get('start_time'),
                   'status': row.get('status'),
                   'modality': row.get('modality'),
                   'room': row.get('room'),
                   'prep_instructions': row.get('prep_instructions', ''),})

    async def post(self, request):
        claims = await self._claims(request)
        if not claims:
            return api_error('INVALID_TOKEN', 'Token invalid or expired',
                             status=403)
        async with get_conn() as conn:
            from db.ris_appointments import RisAppointments
            row = await RisAppointments(conn).mark_checked_in(
                claims['a'], claims['t'])
            if not row:
                return api_error('ALREADY_ARRIVED',
                                 'Appointment not in SCHEDULED state',
                                 status=409)
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='ris.checkin',
                actor_id='',  # kiosk: no user; the token is the actor
                resource_id=claims['a'],
                resource_type='ris_appointments',
                tenant=claims['t'],
            )
        return ok({'id': row['id'], 'status': row['status']})
