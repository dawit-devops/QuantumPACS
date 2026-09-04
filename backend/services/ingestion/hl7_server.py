import asyncio
import hashlib
from datetime import datetime
import ipaddress
import json
import traceback

import hl7

from db.conn import get_conn
from db.patient import Patient
from db.worklist import Worklist
from db.hl7_message import Hl7Message
from log import get_logger

log = get_logger(__name__)

MLLP_START = b'\x0b'
MLLP_END = b'\x1c\x0d'


class MllpServer:
    def __init__(self, host='', port=12579, handler=None, ssl_context=None, allowed_ips=None):
        self._host = host
        self._port = port
        self._handler = handler or default_handler
        self._ssl_context = ssl_context
        self._allowed_networks = []
        for entry in (allowed_ips or []):
            try:
                self._allowed_networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                log.warning('Invalid IP network in allowed_ips: %s', entry)
        self._server = None

    async def start(self):
        self._server = await asyncio.start_server(
            self._on_connect, self._host, self._port,
            ssl=self._ssl_context,
        )
        addr = self._server.sockets[0].getsockname()
        log.info('MLLP server listening on %s:%s', addr[0], addr[1])

    async def stop(self):
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            log.info('MLLP server stopped')

    async def _on_connect(self, reader, writer):
        peer = writer.get_extra_info('peername')
        peer_ip = peer[0] if peer else ''
        if self._allowed_networks:
            try:
                addr = ipaddress.ip_address(peer_ip)
                if not any(addr in net for net in self._allowed_networks):
                    log.warning('MLLP connection rejected from %s (not in whitelist)', peer_ip)
                    writer.close()
                    return
            except ValueError:
                log.warning('MLLP connection rejected from %s (invalid IP)', peer_ip)
                writer.close()
                return
        try:
            while True:
                data = await reader.readuntil(MLLP_END)
                if not data:
                    break
                if data.startswith(MLLP_START):
                    msg_bytes = data[1:-2]
                else:
                    msg_bytes = data[:-2]

                raw_hash = hashlib.sha256(msg_bytes).hexdigest()
                log.info('HL7 message received (SHA-256: %s)', raw_hash[:16])

                try:
                    result = await self._handler(msg_bytes)
                    writer.write(MLLP_START + result + MLLP_END)
                    await writer.drain()
                except Exception:
                    log.exception('handler error')
                    nack = b'NACK'
                    writer.write(MLLP_START + nack + MLLP_END)
                    await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        except Exception:
            log.exception('connection error')
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


async def _store_hl7_message(msg_bytes: bytes, parsed: dict | None, status: str, error: str = ''):
    raw_hash = hashlib.sha256(msg_bytes).hexdigest()
    try:
        raw_body = msg_bytes.decode('utf-8', errors='replace')
        parsed_fields = None
        if parsed:
            cleaned = {k: v for k, v in parsed.items() if v is not None}
            parsed_fields = json.dumps(cleaned)
        async with get_conn() as conn:
            msg = Hl7Message(conn)
            msg_id = await msg.create({
                'raw_hash': raw_hash,
                'raw_content': raw_body,
                'message_type': (parsed or {}).get('message_type', ''),
                'event_type': (parsed or {}).get('event_type', ''),
                'patient_id': (parsed or {}).get('patient_id', ''),
                'accession_number': (parsed or {}).get('accession_number', ''),
                'sending_facility': (parsed or {}).get('sending_facility', ''),
                'parsed_fields': parsed_fields,
                'parse_status': status,
                'error_message': error,
            })
            if status == 'failed':
                from db.hl7_message import Hl7ParseError
                pe = Hl7ParseError(conn)
                await pe.create({
                    'hl7_message_id': msg_id,
                    'segment': 'MSH',
                    'field_name': 'raw_message',
                    'raw_value': raw_body[:500],
                    'error_message': error or 'Unparseable message',
                })
    except Exception:
        log.exception('Failed to store HL7 message')


async def default_handler(msg_bytes: bytes) -> bytes:
    parsed = parse_hl7_message(msg_bytes)
    if parsed is None:
        await _store_hl7_message(msg_bytes, None, 'failed', 'Unparseable message')
        return b'ERR Unparseable message'

    await _store_hl7_message(msg_bytes, parsed, 'ok')

    msg_type = parsed['message_type']
    event_type = parsed['event_type']

    if msg_type == 'ADT':
        success = await handle_adt_message(parsed)
        if not success:
            return b'ERR ADT processing failed'
        log.info('ADT-%s processed for patient %s', event_type, parsed.get('patient_id', '?'))
        return b'ACK'

    if msg_type == 'ORM':
        success = await handle_orm_message(parsed)
        if not success:
            return b'ERR ORM processing failed'
        log.info('ORM-%s processed for accession %s', event_type, parsed.get('accession_number', '?'))
        return b'ACK'

    if msg_type == 'ORU':
        success = await handle_oru_message(parsed)
        if not success:
            return b'ERR ORU processing failed'
        log.info('ORU-%s processed for accession %s', event_type, parsed.get('accession_number', '?'))
        return b'ACK'

    msg_control_id = parsed.get('message_control_id', '?')
    log.warning('Unknown message type: %s^%s id=%s', msg_type, event_type, msg_control_id)
    return b'ACK'


def _seg_field(seg, hl7_field, comp=0, sub=0, default=''):
    if hl7_field >= len(seg) or hl7_field < 0:
        return default
    try:
        val = seg[hl7_field]
        if isinstance(val, str):
            return val
        val = val[comp]
        if isinstance(val, str):
            return val
        val = val[sub]
        return str(val)
    except (IndexError, TypeError):
        return default


def _seg_field_raw(seg, hl7_field, default=''):
    if hl7_field >= len(seg) or hl7_field < 0:
        return default
    try:
        return str(seg[hl7_field])
    except Exception:
        return default


def _obr_procedure(obr) -> dict:
    """Per-OBR procedure entry (B1): every OBR in an ORM is a schedulable
    procedure — the segment map must not collapse them."""
    start_dt = _seg_field(obr, 7, 0, 0)
    return {
        'procedure_code': _seg_field(obr, 3, 0, 0),
        'procedure_desc': _seg_field_raw(obr, 4),
        # Universal service ID components → RequestedProcedureCodeSequence
        # (0008,0100 CodeValue / 0008,0102 Scheme / 0008,0104 CodeMeaning).
        # NOTE: this hl7 lib indexes field[comp] as repetitions and
        # rep[sub] as components — component 0/1/2 = (field, 0, 0/1/2).
        'requested_procedure_code': _seg_field(obr, 4, 0, 0),
        'requested_procedure_code_meaning': _seg_field(obr, 4, 0, 1),
        'requested_procedure_code_scheme': _seg_field(obr, 4, 0, 2),
        'requesting_physician': _seg_field_raw(obr, 16),
        # Ordering provider doubles as the referring physician in most RIS
        # integrations; ZDS-level separation is a later refinement.
        'referring_physician': _seg_field_raw(obr, 16),
        'modality': _seg_field(obr, 24, 0, 0),
        'station_ae_title': _seg_field(obr, 18, 0, 0),
        'scheduled_station_name': _seg_field(obr, 18, 0, 1),
        # OBR-32 principal result interpreter → ScheduledPerformingPhysician.
        'scheduled_performing_physician': _seg_field_raw(obr, 32),
        # OBR-31 reason for study → ReasonForTheRequestedProcedure (0040,1002).
        'reason_for_requested_procedure': _seg_field(obr, 31, 0, 0),
        # OBR-27 Quantity/Timing component 7 (priority: R routine, A ASAP,
        # S stat) → RequestedProcedurePriority (0040,1003).
        'requested_procedure_priority': _seg_field(obr, 27, 0, 5),
        'scheduled_date': start_dt[:8] if start_dt else '',
        'scheduled_time': (
            start_dt[8:14] if len(start_dt) >= 14
            else (start_dt[8:12] if len(start_dt) >= 12 else '')
        ),
        'result_status': _seg_field(obr, 25, 0, 0),
    }


def parse_hl7_message(data) -> dict | None:
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    # Line-ending normalization: python-hl7 splits segments on \r only, so
    # \r\n (Windows senders) leaves the \n glued to the next segment name
    # ('\nPID' never matches 'PID') and bare \n swallows the segment. Real
    # HIS feeds use both — normalize before parsing (S3-05 conformance).
    data = data.replace('\r\n', '\r').replace('\n', '\r')
    try:
        msg = hl7.parse(data)
    except Exception:
        return None

    # Singleton segments: last occurrence wins (feeds never repeat them).
    segments = {seg[0][0]: seg for seg in msg}
    msh = segments.get('MSH')
    if msh is None:
        return None

    result = {
        'message_type': _seg_field(msh, 9, 0, 0),
        'event_type': _seg_field(msh, 9, 0, 1),
        'sending_facility': _seg_field(msh, 4, 0, 0),
        'message_control_id': _seg_field(msh, 10, 0, 0),
    }

    pid = segments.get('PID')
    if pid is not None:
        result['patient_id'] = _seg_field(pid, 3, 0, 0)
        result['patient_name'] = _seg_field_raw(pid, 5)
        result['birth_date'] = _seg_field(pid, 7, 0, 0)
        result['sex'] = _seg_field(pid, 8, 0, 0)
        address = _seg_field(pid, 11, 0, 0)
        result['address'] = address or None

    mrg = segments.get('MRG')
    if mrg is not None:
        result['merged_patient_id'] = _seg_field(mrg, 1, 0, 0)
        result['surviving_patient_id'] = result.get('patient_id', '')

    # B2: PV1 encounter context (S3-02 conformance set) — patient class
    # (PV1-2), attending doctor (PV1-7), visit number (PV1-19).
    pv1 = segments.get('PV1')
    if pv1 is not None:
        result['patient_class'] = _seg_field(pv1, 2, 0, 0)
        result['attending_doctor'] = _seg_field_raw(pv1, 7)
        result['visit_number'] = _seg_field(pv1, 19, 0, 0)

    # B2: DG1 diagnoses — repeatable segment, so collect every occurrence.
    dg1s = [seg for seg in msg if seg[0][0] == 'DG1']
    if dg1s:
        result['diagnoses'] = [
            {
                'code': _seg_field(dg1, 3, 0, 0),
                'description': _seg_field(dg1, 3, 0, 1),
                'coding_system': _seg_field(dg1, 3, 0, 2),
            }
            for dg1 in dg1s
        ]

    orc = segments.get('ORC')
    if orc is not None:
        result['accession_number'] = _seg_field(orc, 2, 0, 0)
        result['order_control'] = _seg_field(orc, 1, 0, 0)

    # B1: collect EVERY OBR — multi-procedure orders are the norm in
    # radiology (bilateral joints, CT abdo+pelvis). First OBR also feeds
    # the legacy top-level scalar fields so single-procedure callers and
    # previously-stored parsed_segments stay compatible.
    obrs = [seg for seg in msg if seg[0][0] == 'OBR']
    if obrs:
        procedures = []
        for idx, obr in enumerate(obrs):
            proc = _obr_procedure(obr)
            procedures.append(proc)
            if idx == 0:
                result['requested_procedure_id'] = proc['procedure_code']
                result['requested_procedure_desc'] = proc['procedure_desc']
                result['requested_procedure_code'] = \
                    proc['requested_procedure_code']
                result['requested_procedure_code_meaning'] = \
                    proc['requested_procedure_code_meaning']
                result['requested_procedure_code_scheme'] = \
                    proc['requested_procedure_code_scheme']
                result['requesting_physician'] = \
                    proc['requesting_physician']
                result['referring_physician'] = \
                    proc['referring_physician']
                result['modality'] = proc['modality']
                result['station_ae_title'] = proc['station_ae_title']
                result['scheduled_station_name'] = \
                    proc['scheduled_station_name']
                result['scheduled_performing_physician'] = \
                    proc['scheduled_performing_physician']
                result['reason_for_requested_procedure'] = \
                    proc['reason_for_requested_procedure']
                result['requested_procedure_priority'] = \
                    proc['requested_procedure_priority']
                result['scheduled_date'] = proc['scheduled_date']
                result['scheduled_time'] = proc['scheduled_time']
                # ORU^R01 carries no ORC segment; the accession rides in
                # OBR-3 (filler order number) or OBR-2 (placer order no.).
                if not result.get('accession_number'):
                    result['accession_number'] = \
                        _seg_field(obr, 3, 0, 0) or _seg_field(obr, 2, 0, 0)
                result['result_status'] = proc['result_status']
        result['procedures'] = procedures

    return result


async def handle_adt_message(parsed: dict) -> bool:
    event = parsed.get('event_type', '')
    patient_id = parsed.get('patient_id', '')
    if not patient_id:
        return False

    # S3-20 / R2-06-06: HIS pre-registration — patient record plus an
    # unassigned appointment stub so front desk never re-keys the visit.
    if event == 'Z01':
        return await _preregister_patient(parsed)

    if event == 'A03':
        data = {'patient_id': patient_id}
        return await _deactivate_patient(data)

    if event in ('A01', 'A02', 'A04', 'A05', 'A08'):
        data = {
            'patient_id': patient_id,
            'patient_name': parsed.get('patient_name', ''),
            'patient_birth_date': parsed.get('birth_date', ''),
            'patient_sex': parsed.get('sex', ''),
            'sending_facility': parsed.get('sending_facility', ''),
        }
        return await _upsert_patient(data)

    if event in ('A06', 'A40'):
        surviving_id = parsed.get('surviving_patient_id', '')
        merged_id = parsed.get('merged_patient_id', '')
        if not surviving_id or not merged_id:
            return False
        return await _merge_patients(surviving_id, parsed, merged_id)

    if event == 'A07':
        surviving_id = parsed.get('surviving_patient_id', '')
        merged_id = parsed.get('merged_patient_id', '')
        if not surviving_id or not merged_id:
            return False
        return await _unmerge_patients(surviving_id, parsed, merged_id)

    log.warning('Unknown ADT event: %s for patient %s', event, patient_id)
    return False


async def _preregister_patient(parsed: dict) -> bool:
    try:
        async with get_conn() as conn:
            await Patient(conn).insert_or_select({
                'patient_id': parsed.get('patient_id', ''),
                'patient_name': parsed.get('patient_name', ''),
                'patient_birth_date': parsed.get('birth_date', ''),
                'patient_sex': parsed.get('sex', ''),
                'sending_facility': parsed.get('sending_facility', ''),
            })
            sd = parsed.get('scheduled_date', '')
            if not sd:
                return True  # registration only; slot comes later
            stime = (parsed.get('scheduled_time') or '').replace(':', '')
            stime = stime.ljust(6, '0')[:6] or '000000'
            try:
                start = datetime.strptime(sd + stime, '%Y%m%d%H%M%S')
            except ValueError:
                log.warning('Z01 unparsable schedule %s/%s — registered '
                            'patient without booking', sd, stime)
                return True
            from datetime import timedelta
            from db.conn import get_tenant_slug
            from db.ris_appointments import RisAppointments
            tenant = get_tenant_slug() or (
                parsed.get('sending_facility') or 'default').lower()
            await RisAppointments(conn).create({
                'tenant_id': tenant,
                # resource stays NULL until staff assign a room/device;
                # EXCLUDE guard treats NULLs as distinct so stubs never
                # collide with real bookings (migration 085).
                'resource_id': None,
                'patient_id': parsed.get('patient_id', ''),
                'start_time': start,
                'end_time': start + timedelta(minutes=30),
                'status': 'SCHEDULED',
                'reason': 'HL7 pre-registration (ADT^Z01)',
                'created_by': 'hl7:adt-z01',
            })
        return True
    except Exception:
        log.exception('Z01 pre-registration failed for %s',
                      parsed.get('patient_id'))
        return False


async def _upsert_patient(data: dict) -> bool:
    try:
        async with get_conn() as conn:
            p = Patient(conn)
            await p.insert_or_select(data)
            pid = data.get('patient_id', '')
            if pid:
                facility = data.get('sending_facility', '')
                # Parameterized everywhere: facility comes from the wire
                # (MSH-4) and must never be interpolated into SQL. jsonb_set
                # with an empty path ('{}') is a no-op, so merge keys with ||.
                if facility:
                    await conn.execute(
                        "UPDATE patients SET meta = COALESCE(meta, '{}'::jsonb) || "
                        "jsonb_build_object('sync_source', 'hl7', 'tenant_id', $2::text) "
                        "WHERE patient_id = $1",
                        pid,
                        facility,
                    )
                else:
                    await conn.execute(
                        "UPDATE patients SET meta = COALESCE(meta, '{}'::jsonb) || "
                        "jsonb_build_object('sync_source', 'hl7') "
                        "WHERE patient_id = $1",
                        pid,
                    )
        return True
    except Exception:
        log.exception('patient upsert failed')
        return False


async def _deactivate_patient(data: dict) -> bool:
    try:
        async with get_conn() as conn:
            q = "UPDATE patients SET meta = jsonb_set(COALESCE(meta, '{}'), '{active}', to_jsonb(false)) WHERE patient_id = $1"
            await conn.execute(q, data['patient_id'])
        return True
    except Exception:
        log.exception('patient deactivation failed')
        return False


async def _merge_patients(surviving_id: str, parsed: dict, merged_id: str) -> bool:
    try:
        async with get_conn() as conn:
            from db.patient import Patient as PatientModel
            p = PatientModel(conn)
            await p.insert_or_select({
                'patient_id': surviving_id,
                'patient_name': parsed.get('patient_name', ''),
                'patient_birth_date': parsed.get('birth_date', ''),
                'patient_sex': parsed.get('sex', ''),
            })
            # B3 (S3-12): merges must propagate. Re-point every RIS
            # reference from the merged-away MRN to the survivor inside
            # one transaction, otherwise schedulers/techs lose sight of
            # live work the moment the HIS collapses duplicate MRNs.
            async with conn.transaction():
                await conn.execute(
                    "UPDATE ris_orders SET patient_id = $1"
                    " WHERE patient_id = $2",
                    surviving_id, merged_id,
                )
                await conn.execute(
                    "UPDATE ris_appointments SET patient_id = $1"
                    " WHERE patient_id = $2",
                    surviving_id, merged_id,
                )
                await conn.execute(
                    "UPDATE worklist_entries SET patient_id = $1"
                    " WHERE patient_id = $2",
                    surviving_id, merged_id,
                )
            await conn.execute(
                # to_jsonb() gives an explicit jsonb argument — a $n::text
                # expression will not implicitly cast (jsonb_set has no
                # (jsonb, text[], text) overload).
                "UPDATE patients SET meta = jsonb_set(COALESCE(meta, '{}'), '{merged_into}', to_jsonb($1::text)) WHERE patient_id = $2",
                surviving_id, merged_id,
            )
            await conn.execute(
                "UPDATE patients SET meta = jsonb_set(COALESCE(meta, '{}'), '{active}', to_jsonb(false)) WHERE patient_id = $1",
                merged_id,
            )
            # B3: audit the propagation with per-table re-point counts so
            # MPI operators can verify what moved (0-count merges are legal).
            counts = await conn.fetchrow(
                "SELECT"
                " (SELECT count(*) FROM ris_orders WHERE patient_id = $1) AS orders,"
                " (SELECT count(*) FROM ris_appointments WHERE patient_id = $1) AS appointments,"
                " (SELECT count(*) FROM worklist_entries WHERE patient_id = $1) AS worklist",
                surviving_id,
            )
            try:
                from db.audit_log import AuditLog
                from db.conn import get_tenant_slug
                await AuditLog(conn).log_event(
                    event_type='mpi.hl7_merged',
                    actor_id='hl7',
                    resource_type='patient',
                    resource_id=surviving_id,
                    details={
                        'merged_patient_id': merged_id,
                        'orders': int(counts['orders']),
                        'appointments': int(counts['appointments']),
                        'worklist': int(counts['worklist']),
                    },
                    tenant=get_tenant_slug(),
                )
            except Exception:
                log.warning('merge audit failed for %s->%s',
                            merged_id, surviving_id, exc_info=True)
        return True
    except Exception:
        log.exception('patient merge failed')
        return False


async def _unmerge_patients(surviving_id: str, parsed: dict, merged_id: str) -> bool:
    try:
        async with get_conn() as conn:
            from db.patient import Patient as PatientModel
            p = PatientModel(conn)
            await p.insert_or_select({
                'patient_id': surviving_id,
                'patient_name': parsed.get('patient_name', ''),
                'patient_birth_date': parsed.get('birth_date', ''),
                'patient_sex': parsed.get('sex', ''),
            })
            await conn.execute(
                "UPDATE patients SET meta = (meta - 'merged_into') WHERE patient_id = $1",
                merged_id,
            )
            await conn.execute(
                "UPDATE patients SET meta = jsonb_set(COALESCE(meta, '{}'), '{active}', to_jsonb(true)) WHERE patient_id = $1",
                merged_id,
            )
        return True
    except Exception:
        log.exception('patient unmerge failed')
        return False


async def handle_orm_message(parsed: dict) -> bool:
    patient_id = parsed.get('patient_id', '')
    accession = parsed.get('accession_number', '')
    if not patient_id or not accession:
        return False

    birth_date = parsed.get('birth_date', '')
    sex = parsed.get('sex', '')
    patient_name = parsed.get('patient_name', '')

    try:
        async with get_conn() as conn:
            p = Patient(conn)
            await p.insert_or_select({
                'patient_id': patient_id,
                'patient_name': patient_name,
                'patient_birth_date': birth_date,
                'patient_sex': sex,
            })

            wl = Worklist(conn)
            existing = await wl.get_by_accession(accession)
            entry_data = {
                'patient_id': patient_id,
                'patient_name': patient_name,
                'patient_birth_date': birth_date,
                'patient_sex': sex,
                'accession_number': accession,
                'requested_procedure_id': parsed.get('requested_procedure_id', ''),
                'requested_procedure_desc': parsed.get('requested_procedure_desc', ''),
                'requested_procedure_priority': parsed.get('requested_procedure_priority', ''),
                'reason_for_requested_procedure': parsed.get('reason_for_requested_procedure', ''),
                'requested_procedure_code': parsed.get('requested_procedure_code', ''),
                'requested_procedure_code_meaning': parsed.get('requested_procedure_code_meaning', ''),
                'requested_procedure_code_scheme': parsed.get('requested_procedure_code_scheme', ''),
                'requesting_physician': parsed.get('requesting_physician', ''),
                'referring_physician': parsed.get('referring_physician', ''),
                'scheduled_station_name': parsed.get('scheduled_station_name', ''),
                'scheduled_performing_physician': parsed.get('scheduled_performing_physician', ''),
                'modality': parsed.get('modality', ''),
                'station_ae_title': parsed.get('station_ae_title', ''),
                'scheduled_date': parsed.get('scheduled_date', ''),
                'scheduled_time': parsed.get('scheduled_time', ''),
            }

            # ORC-1 order control: CA (cancel) / OC (order canceled) / DC
            # (discontinue) cancel a previously scheduled entry. Re-sends
            # (NW/SC/RO) update the existing scheduling data instead of being
            # silently dropped.
            order_control = parsed.get('order_control', '')
            if existing:
                if order_control in ('CA', 'OC', 'DC') and existing.get('status') == 'scheduled':
                    await wl.cancel(existing['id'])
                    log.info('ORM-%s cancelled worklist entry %s', order_control, existing['id'])
                elif existing.get('status') == 'scheduled':
                    await wl.update_entry(existing['id'], entry_data)
                    log.info('ORM-%s updated worklist entry %s', order_control or 'RE', existing['id'])
                return True

            await wl.create(entry_data)
        return True
    except Exception:
        log.exception('ORM processing failed')
        return False


async def handle_oru_message(parsed: dict) -> bool:
    """ORU^R01 — results reported: the study is complete.

    ME-05: ORU messages were ACKed and dropped. A results message is the
    authoritative 'performed' signal — a partial study (instances stored
    but no results) must not flip the MWL entry to performed, so this
    handler, not C-STORE, is the only path that marks it performed.
    """
    accession = parsed.get('accession_number', '')
    patient_id = parsed.get('patient_id', '')
    if not accession:
        return False

    try:
        async with get_conn() as conn:
            # ME-05: a results message is the authoritative 'study complete'
            # signal — flip any study carrying this accession before the MWL
            # bookkeeping (which may legitimately have no entry at all).
            try:
                await conn.execute(
                    "UPDATE studies SET study_status = 'complete' "
                    "WHERE accession_number = $1 AND study_status != 'complete'",
                    accession,
                )
            except Exception:
                log.warning('Study complete update failed: %s', traceback.format_exc())

            if patient_id:
                p = Patient(conn)
                await p.insert_or_select({
                    'patient_id': patient_id,
                    'patient_name': parsed.get('patient_name', ''),
                    'patient_birth_date': parsed.get('birth_date', ''),
                    'patient_sex': parsed.get('sex', ''),
                })

            wl = Worklist(conn)
            existing = await wl.get_by_accession(accession)
            if not existing:
                log.info('ORU for unknown accession %s (no MWL entry)', accession)
                return True
            if existing.get('status') in ('performed', 'cancelled'):
                return True
            await wl.mark_performed(accession)
            log.info('ORU marked worklist entry %s performed', accession)
        return True
    except Exception:
        log.exception('ORU processing failed')
        return False
