"""HL7 interface engine (S3-01/01b/02/03/08).

Single entry point for inbound HL7 (HTTP receiver + MLLP listener):
parse → persist (ris_hl7_messages status lifecycle RECEIVED→PARSED→
PROCESSED / FAILED + legacy hl7_messages audit mirror) → route → ACK/ERR.
Failures land in the exception queue (status FAILED, retry_count) and can
be replayed via retry_failed() — nothing is dropped silently (S3-03).

Routing reuses the ingestion handlers for ADT/ORU and adds the S3-08
ORM→ris_orders path. The existing ORM worklist/patient processing is
preserved so modalities keep their MWL feed while orders start flowing
to ris_orders. The response contract matches the legacy default_handler:
b'ACK' on success, b'ERR ...' on failure.
"""

import hashlib
import json
import time

from api.telemetry import ris_hl7_message_latency_seconds, ris_hl7_messages_total
from db.conn import get_conn
from db.ris_hl7 import RisHl7Messages, RisInterfaceEndpoints, RisInterfaceEvents
from db.ris_orders import RisOrders, RisOrderProcedures
from log import get_logger
from services.hl7_engine.alerts import notify_interface_failure
from services.hl7_engine.parser import (
    Hl7ValidationError,
    normalize_priority,
    parse_hl7_message,
    to_date,
    validate,
)
from services.ingestion.hl7_server import (
    _store_hl7_message,
    handle_adt_message,
    handle_orm_message,
    handle_oru_message,
)

log = get_logger(__name__)


class Hl7InterfaceEngine:
    """Parses, persists, routes, and retries inbound HL7 messages."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def receive_message(self, raw: bytes, endpoint_id=None) -> bytes:
        """Process one MLLP-framed message; returns the ACK/ERR byte reply."""
        started = time.monotonic()
        raw_hash = hashlib.sha256(raw).hexdigest()
        parsed = parse_hl7_message(raw)
        if parsed is None:
            self._record('', '', 'FAILED')
            await self._persist(raw, raw_hash, None, 'FAILED', 'Unparseable message', endpoint_id)
            await _store_hl7_message(raw, None, 'failed', 'Unparseable message')
            return b'ERR Unparseable message'

        try:
            validate(parsed)
        except Hl7ValidationError as exc:
            self._record(parsed.get('message_type', ''), parsed.get('event_type', ''), 'FAILED')
            await self._persist(raw, raw_hash, parsed, 'FAILED', str(exc), endpoint_id)
            await _store_hl7_message(raw, parsed, 'failed', str(exc))
            return f'ERR {exc}'.encode()

        self._record(parsed['message_type'], parsed.get('event_type', ''), 'RECEIVED')
        if endpoint_id is None:
            endpoint_id = await self._resolve_endpoint(parsed)
        msg_id = await self._persist(raw, raw_hash, parsed, 'RECEIVED', '', endpoint_id)
        await _store_hl7_message(raw, parsed, 'ok')
        await self._mark(msg_id, 'PARSED')

        msg_type = parsed['message_type']
        try:
            ok = await self._route(parsed)
        except Exception as exc:
            log.exception('HL7 %s^%s processing failed', msg_type, parsed.get('event_type', '?'))
            self._record(msg_type, parsed.get('event_type', ''), 'FAILED')
            await self._mark(msg_id, 'FAILED', error=str(exc))
            await self._alert_failure(parsed, str(exc), endpoint_id)
            await self._event(parsed, 'HL7_PROCESSING_ERROR', 'ERROR', str(exc), endpoint_id)
            ris_hl7_message_latency_seconds.observe(time.monotonic() - started)
            return f'ERR {msg_type} processing failed'.encode()

        if not ok:
            self._record(msg_type, parsed.get('event_type', ''), 'FAILED')
            await self._mark(msg_id, 'FAILED', error=f'{msg_type} handler returned False')
            await self._alert_failure(parsed, f'{msg_type} handler returned False', endpoint_id)
            await self._event(
                parsed, 'HL7_PROCESSING_ERROR', 'ERROR',
                f'{msg_type} handler returned False', endpoint_id,
            )
            ris_hl7_message_latency_seconds.observe(time.monotonic() - started)
            return f'ERR {msg_type} processing failed'.encode()

        self._record(msg_type, parsed.get('event_type', ''), 'PROCESSED')
        await self._mark(msg_id, 'PROCESSED')
        await self._event(parsed, 'HL7_PROCESSED', 'INFO', f'{msg_type} processed', endpoint_id)
        ris_hl7_message_latency_seconds.observe(time.monotonic() - started)
        return b'ACK'

    @staticmethod
    def _record(msg_type: str, trigger: str, status: str):
        ris_hl7_messages_total.labels(type=msg_type, trigger=trigger, status=status).inc()

    _ENDPOINT_TYPES = {'ORM': 'HL7_ORM', 'ADT': 'HL7_ADT', 'ORU': 'HL7_ORU'}

    async def _resolve_endpoint(self, parsed: dict):
        """Map a live message to its interface endpoint (S3-16 dashboard).

        The legacy listener never registered endpoints, so the dashboard
        would be permanently empty on feeds that predate the registry.
        Resolve-or-create from the MSH sending application/facility instead:
        the first message of a feed creates its row, later ones reuse it,
        and _persist() keeps the counters/last_message_at current.
        """
        iface_type = self._ENDPOINT_TYPES.get(parsed.get('message_type'))
        if not iface_type:
            return None
        name = f"{parsed.get('sending_app', '')} {parsed.get('sending_facility', '')}".strip() or 'HL7 feed'
        try:
            async with get_conn() as conn:
                endpoints = RisInterfaceEndpoints(conn)
                row = await endpoints.get_by_name(name)
                if row:
                    return row['id']
                created_id = await endpoints.create({
                    'name': name,
                    'interface_type': iface_type,
                    'protocol': 'HL7V2',
                    'config': {},
                })
                log.info('Registered interface endpoint %s (%s)', name, iface_type)
                return created_id
        except Exception:
            log.warning('Endpoint resolution failed for %s — persisting unattached', name)
            return None

    async def retry_failed(self, limit=50) -> int:
        """Replay the exception queue; returns how many messages were retried.

        Each FAILED message below its retry budget is re-parsed from the
        stored raw message and routed again — success flips it to
        PROCESSED, failure increments retry_count so the budget is
        visible in the queue. Manual reconcile entry point (S3-03).
        """
        async with get_conn() as conn:
            messages = RisHl7Messages(conn)
            failed = await messages.list_failed(limit=limit, max_retries=self.max_retries)
            for row in failed:
                await self._retry_one(messages, row)
        return len(failed)

    async def retry_message(self, msg_id) -> bool:
        """Replay a single FAILED message (S3-16 exception-queue retry).

        Returns True when the message was replayed and reached PROCESSED;
        False when it is unknown, past its retry budget, or failed again.
        """
        async with get_conn() as conn:
            messages = RisHl7Messages(conn)
            row = await messages.get(msg_id)
            if not row or row['status'] != 'FAILED' or row['retry_count'] >= self.max_retries:
                return False
            return await self._retry_one(messages, row)

    async def _retry_one(self, messages, row) -> bool:
        msg_id = row['id']
        await messages.update_status(msg_id, 'RETRYING')
        try:
            parsed = parse_hl7_message(row['raw_message'])
            if parsed is None:
                raise Hl7ValidationError('Unparseable message')
            validate(parsed)
            if not await self._route(parsed):
                raise Hl7ValidationError(
                    f"{parsed.get('message_type')} handler returned False",
                )
        except Exception as exc:
            attempt = row['retry_count'] + 1
            await messages.update_status(
                msg_id, 'FAILED',
                error=f'{exc} (retry {attempt}/{self.max_retries})',
                retry_count=attempt,
            )
            log.warning('HL7 retry %s/%s failed for %s', attempt, self.max_retries, msg_id)
            return False
        await messages.update_status(msg_id, 'PROCESSED')
        log.info('HL7 retry succeeded for %s', msg_id)
        return True

    async def _route(self, parsed: dict) -> bool:
        msg_type = parsed['message_type']
        if msg_type == 'ADT':
            return await handle_adt_message(parsed)
        if msg_type == 'ORM':
            return await self._handle_orm(parsed)
        if msg_type == 'ORU':
            return await handle_oru_message(parsed)
        # Unknown types are ACKed and persisted (legacy behavior): the
        # message is on record, so nothing is dropped silently.
        log.warning(
            'Unknown message type: %s^%s id=%s',
            msg_type, parsed.get('event_type', '?'), parsed.get('message_control_id', '?'),
        )
        return True

    async def _handle_orm(self, parsed: dict) -> bool:
        """ORM^O01 — patient/worklist path (legacy) + ris_orders (S3-08)."""
        if not await handle_orm_message(parsed):
            return False
        accession = parsed.get('accession_number', '')
        # B2: OBR-31 reason first; DG1 diagnoses as the visible fallback so
        # the order carries a human-readable *why* either way.
        indication = parsed.get('reason_for_requested_procedure', '')
        if not (indication or '').strip():
            diagnoses = parsed.get('diagnoses') or []
            descriptions = [d.get('description', '') for d in diagnoses
                            if d.get('description')]
            indication = '; '.join(descriptions)
        async with get_conn() as conn:
            # Re-sends (NW/SC/RO for an existing accession) are idempotent:
            # the order already exists; do not duplicate it.
            existing = await RisOrders(conn).get_by_accession(accession)
            if existing:
                return True
            order = await RisOrders(conn).create({
                'accession_number': accession,
                'patient_id': parsed.get('patient_id', ''),
                'patient_name': parsed.get('patient_name', ''),
                'patient_dob': to_date(parsed.get('birth_date', '')),
                'referring_physician': parsed.get('referring_physician', ''),
                'clinical_indication': indication,
                'priority': normalize_priority(parsed.get('requested_procedure_priority', '')),
                'created_by': f"hl7:{parsed.get('sending_facility', '')}",
            })
            # B1: one procedure row per OBR. Parsed payloads stored before
            # the multi-OBR fix (exception-queue replays) lack the
            # 'procedures' key — fall back to the top-level scalar fields
            # so a replay never loses its single procedure.
            procedures = parsed.get('procedures')
            if not procedures:
                procedures = [{
                    'procedure_code': parsed.get('requested_procedure_id', ''),
                    'requested_procedure_code_meaning':
                        parsed.get('requested_procedure_code_meaning'),
                    'procedure_desc':
                        parsed.get('requested_procedure_desc', ''),
                    'modality': parsed.get('modality', ''),
                }]
            for proc in procedures:
                await RisOrderProcedures(conn).create(order['id'], {
                    'procedure_code': proc.get('procedure_code', ''),
                    'procedure_name': (
                        proc.get('requested_procedure_code_meaning')
                        or proc.get('procedure_desc', '')
                    ),
                    'modality': proc.get('modality', ''),
                })
            log.info(
                'ORM^O01 created order for accession %s (facility %s)',
                accession, parsed.get('sending_facility', '?'),
            )
        return True

    async def _persist(self, raw: bytes, raw_hash: str, parsed, status: str,
                       error: str, endpoint_id):
        try:
            async with get_conn() as conn:
                msg_id = await RisHl7Messages(conn).create({
                    'endpoint_id': endpoint_id,
                    'message_type': (parsed or {}).get('message_type', ''),
                    'trigger_event': (parsed or {}).get('event_type', ''),
                    'control_id': (parsed or {}).get('message_control_id', ''),
                    'raw_message': raw.decode('utf-8', errors='replace'),
                    'parsed_segments': json.dumps(parsed) if parsed else None,
                    'status': status,
                    'error_message': error,
                    'max_retries': self.max_retries,
                })
                if endpoint_id:
                    await RisInterfaceEndpoints(conn).touch(
                        endpoint_id, 'failed' if status == 'FAILED' else 'ok',
                    )
                if status == 'FAILED':
                    await self._alert_failure(parsed, error, endpoint_id)
                return msg_id
        except Exception:
            # Best-effort audit: the exception queue must never break the
            # wire contract (ACK/ERR) — same resilience as the legacy
            # _store_hl7_message, which swallows its own failures.
            log.exception('Failed to persist HL7 message (sha256 %s)', raw_hash[:16])
            return None

    async def _alert_failure(self, parsed, error, endpoint_id):
        """≤5-min failure alerting (S3-17 / G5).

        Best-effort like every observability path: a failing notification
        fan-out must never break the wire contract (ACK/ERR).
        """
        try:
            async with get_conn() as conn:
                await notify_interface_failure(
                    conn, endpoint_id=endpoint_id, parsed=parsed, error=error,
                )
        except Exception:
            log.exception('Interface failure alert skipped')

    async def _mark(self, msg_id, status: str, error=''):
        if msg_id is None:
            return
        try:
            async with get_conn() as conn:
                await RisHl7Messages(conn).update_status(msg_id, status, error=error)
        except Exception:
            log.exception('Failed to update HL7 message %s to %s', msg_id, status)

    async def _event(self, parsed, event_type: str, severity: str,
                     message: str, endpoint_id):
        try:
            async with get_conn() as conn:
                await RisInterfaceEvents(conn).create({
                    'endpoint_id': endpoint_id,
                    'event_type': event_type,
                    'severity': severity,
                    'message': message,
                    'metadata': {
                        'message_type': parsed.get('message_type', ''),
                        'trigger_event': parsed.get('event_type', ''),
                        'control_id': parsed.get('message_control_id', ''),
                    },
                })
        except Exception:
            # Observability must never break message flow.
            log.exception('Failed to record interface event %s', event_type)