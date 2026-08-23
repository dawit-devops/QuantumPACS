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
from api.schemas.checkin import SubmitConsentRequest, SubmitPaymentRequest
from api.validate import parse_body
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


class PortalCheckInConsentHandler(HTTPEndpoint):
    """K-03: POST /ris/checkin/{token}/consent — persist the kiosk digital
    consent (signature PNG base64, acceptance, or decline with reason).
    Token-authenticated like check-in; refusal still allows check-in."""

    async def post(self, request):
        claims = verify_checkin_token(request.path_params['token'])
        if not claims:
            return api_error('INVALID_TOKEN', 'Token invalid or expired',
                             status=403)
        body = await parse_body(SubmitConsentRequest, request)
        async with get_conn() as conn:
            from db.ris_appointments import RisAppointments
            row = await RisAppointments(conn).record_consent(
                claims['a'], claims['t'], body.accepted,
                body.signature_png, body.decline_reason)
            if not row:
                return not_found('Appointment not found')
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='ris.consent_signed' if body.accepted
                           else 'ris.consent_declined',
                actor_id='',  # kiosk: the token is the actor
                resource_id=claims['a'],
                resource_type='ris_appointments',
                tenant=claims['t'],
                details={'accepted': body.accepted},
            )
        return ok({'id': row['id'], 'accepted': body.accepted})


class PortalCheckInPaymentHandler(HTTPEndpoint):
    """K-04: POST /ris/checkin/{token}/payment — co-pay capture at the
    kiosk. The token is the credential; the appointment's order resolves
    the patient's invoice (order-linked). Payment/balance/receipt reuse
    the billing machinery; no operator attribution (the kiosk is the
    actor)."""

    async def post(self, request):
        claims = verify_checkin_token(request.path_params['token'])
        if not claims:
            return api_error('INVALID_TOKEN', 'Token invalid or expired',
                             status=403)
        body = await parse_body(SubmitPaymentRequest, request)
        async with get_conn() as conn:
            # Duplicate detection first (mirrors BillingPaymentsHandler).
            dup = await conn.fetchval(
                'SELECT 1 FROM payment WHERE idempotency_key = $1',
                body.idempotency_key,
            )
            if dup:
                return ok({'data': {'duplicate': True}})

            # Resolve the appointment -> order -> invoice.
            appt = await conn.fetchrow(
                'SELECT id, order_id, patient_id FROM ris_appointments'
                ' WHERE id::text = $1 AND tenant_id = $2',
                claims['a'], claims['t'],
            )
            if not appt or not appt['order_id']:
                return not_found('Appointment or order not found')

            invoice = await conn.fetchrow(
                'SELECT * FROM invoice WHERE order_id = $1 ORDER BY created_at'
                ' LIMIT 1',
                appt['order_id'],
            )
            if not invoice:
                invoice = await conn.fetchrow(
                    """INSERT INTO invoice
                           (patient_id, order_id, total_amount, paid_amount,
                            balance, status, created_by)
                       VALUES ($1, $2, $3, 0, $3, 'open', 'kiosk')
                       RETURNING *""",
                    appt['patient_id'], appt['order_id'],
                    round(body.amount, 2),
                )
            balance = float(invoice['balance'])
            if body.amount > balance:
                return api_error(
                    'PAYMENT_EXCEEDS_BALANCE',
                    'Payment exceeds outstanding balance',
                    status=422,
                )

            payment = await conn.fetchrow(
                """INSERT INTO payment
                       (invoice_id, method, amount, operator_id,
                        processor_token, idempotency_key)
                   VALUES ($1, $2, $3, '', $4, $5)
                   RETURNING *""",
                invoice['id'], body.method, round(body.amount, 2),
                body.processor_token, body.idempotency_key,
            )
            new_paid = round(float(invoice['paid_amount']) + body.amount, 2)
            status = ('paid' if new_paid >= float(invoice['total_amount'])
                      else 'partially_paid')
            new_balance = round(float(invoice['total_amount']) - new_paid, 2)
            await conn.execute(
                """UPDATE invoice SET paid_amount = $2, balance = $3,
                       status = $4, updated_at = now() WHERE id = $1""",
                invoice['id'], new_paid, new_balance, status,
            )
            receipt = await conn.fetchrow(
                """INSERT INTO receipt (payment_id, receipt_number)
                   VALUES ($1, $2)
                   RETURNING id, payment_id, receipt_number""",
                payment['id'], f'K{payment["id"][:8].upper()}',
            )
            from db.audit_log import AuditLog
            await AuditLog(conn).log_event(
                event_type='ris.copay_collected',
                actor_id='',  # kiosk: the token is the actor
                resource_id=claims['a'],
                resource_type='ris_appointments',
                tenant=claims['t'],
                details={
                    'invoice_id': invoice['id'],
                    'method': body.method,
                    'amount': round(body.amount, 2),
                },
            )
        return ok({'data': {
            'payment': {'id': payment['id'], 'amount': round(body.amount, 2),
                        'method': body.method},
            'receipt': dict(receipt),
        }})


class PortalCheckInQueueHandler(HTTPEndpoint):
    """K-05: GET /ris/checkin/{token}/queue-position — after check-in the
    kiosk shows the patient's place in the queue and an ETA based on how
    many ARRIVED appointments on the same resource are ahead."""

    # Nominal service minutes per position when no real service-time data
    # exists; conservative so the ETA never under-promises.
    MINUTES_PER_POSITION = 15

    async def get(self, request):
        claims = verify_checkin_token(request.path_params['token'])
        if not claims:
            return api_error('INVALID_TOKEN', 'Token invalid or expired',
                             status=403)
        async with get_conn() as conn:
            from db.ris_appointments import RisAppointments
            position = await RisAppointments(conn).queue_position(
                claims['a'], claims['t'])
            if position is None:
                return not_found('Appointment not found')
        eta = max(1, (position - 1)) * self.MINUTES_PER_POSITION
        return ok({'data': {'position': position, 'eta_minutes': eta}})
