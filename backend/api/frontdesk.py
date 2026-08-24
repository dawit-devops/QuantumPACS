"""Front Desk (R08) endpoints — patient registration, visits, order intake,
appointment scheduling with capacity conflict detection, consent capture,
insurance/guarantor records and the privacy-projected waiting queue.

All mutations are audit-logged; the waiting queue applies HIPAA minimum
necessary projection (initials + last-4 of MRN, never full names).
"""
import time as _time
import uuid
import zlib
from datetime import date, datetime, time

from asyncpg.exceptions import UniqueViolationError
from starlette.endpoints import HTTPEndpoint

from api.rbac import requires_permission
from api.permissions import Permission
from api.response import api_error, created, not_found, ok, validation_error
from api.validate import parse_body
from api.schemas.frontdesk import (
    AttachConsentRequest, CreateAppointmentRequest, CreateConsentRequest,
    CreateInsuranceRequest, CreateOrderRequest, CreatePatientRequest,
    CreateVisitRequest, MergePatientsRequest, UndoMergeRequest,
    UpdateInsuranceRequest, UpdatePatientRequest, UpdateVisitRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.frontdesk import FrontDesk
from log import request_id_var
from api.tenant_middleware import effective_tenant


def _row_dict(row):
    """Serialize a DB row for JSON responses — date/time/uuid become strings."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (date, datetime, time, uuid.UUID)):
            d[k] = str(v)
    return d


def _slot_key(t):
    return f'{t.hour:02d}:{t.minute:02d}'


# The single canonical visit lifecycle (R5-10): each status may only move to
# the next state; 'complete' is terminal. The appointment/worklist/exam status
# vocabularies are separate projections of the same booking — the visit is the
# patient-facing lifecycle and the only one a front-desk caller may mutate.
_VISIT_TRANSITIONS = {
    'registered': {'checked_in'},
    'checked_in': {'in_progress'},
    'in_progress': {'complete'},
    'complete': set(),
}


class PatientsSearchHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return ok({'data': []})
        async with get_conn() as conn:
            rows = await FrontDesk(conn).search_patients(q)
        return ok({'data': [_row_dict(r) for r in rows]})


async def _register_patient(conn, request, body):
    """Shared register path for the legacy and RIS patient endpoints — the
    MPI pre-check (R5-13) must behave identically whichever contract the
    front desk uses."""
    fd = FrontDesk(conn)
    patient_id = (body.patient_id or '').strip() or f'P{int(_time.time() * 1000)}'
    name = body.name.strip()
    existing = await fd.find_patient_duplicate(
        name, body.birth_date, (body.phone or '').strip())
    if existing:
        return api_error(
            'PATIENT_EXISTS',
            'Patient with this name and birth date already exists',
            details={'patient': _row_dict(existing)},
            status=409,
        )
    try:
        row = await fd.create_patient({
            'patient_id': patient_id,
            'name': name,
            'birth_date': body.birth_date,
            'sex': body.sex,
            'phone': body.phone,
            'email': body.email,
            'meta': body.meta,
        })
    except UniqueViolationError:
        return validation_error('Patient with this ID already exists')
    # FD-01: MPI soft alert — the exact match missed, but a fuzzy trigram
    # match on the name is a probable duplicate the front desk should flag.
    warning = None
    try:
        fuzzy = await fd.search_patients_fuzzy(name, threshold=0.3, limit=1)
    except Exception:
        fuzzy = []
    if fuzzy:
        match = fuzzy[0]
        warning = {
            'existing_patient_id': match['patient_id'],
            'existing_patient_name': match['name'],
        }
    await AuditLog(conn).log_event(
        event_type='frontdesk.patient_registered',
        actor_id=request.user.id,
        resource_type='patient',
        resource_id=row['id'],
        details={'patient_id': patient_id},
        tenant=effective_tenant(request),
        request_id=request_id_var.get(),
    )
    data = _row_dict(row)
    if warning:
        data['warning'] = warning
    return created({'data': data})


class PatientsRegistrationHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        body = await parse_body(CreatePatientRequest, request)
        async with get_conn() as conn:
            return await _register_patient(conn, request, body)


# ---- RIS patient contract (§4.1) ----
# Same registration/search/insurance logic as the legacy frontdesk endpoints,
# gated by the RIS permission vocabulary (PATIENT_READ/PATIENT_WRITE) and
# adding update + check-in, which the legacy contract never exposed.


class RisPatientsHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        body = await parse_body(CreatePatientRequest, request)
        async with get_conn() as conn:
            return await _register_patient(conn, request, body)


class RisPatientsSearchHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        # FD-07: search by name/MRN (q), DOB, or phone — the quick-search
        # overlay fires whichever field the user filled.
        q = (request.query_params.get('q') or '').strip()
        dob = (request.query_params.get('dob') or '').strip()
        phone = (request.query_params.get('phone') or '').strip()
        if len(q) < 2 and not dob and not phone:
            return ok({'data': []})
        async with get_conn() as conn:
            rows = await FrontDesk(conn).search_patients(q, dob=dob, phone=phone)
        return ok({'data': [_row_dict(r) for r in rows]})


class RisPatientHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        patient_id = request.path_params['id']
        async with get_conn() as conn:
            row = await FrontDesk(conn).get_patient(patient_id)
        if not row:
            return not_found('Patient not found')
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.PATIENT_WRITE)
    async def put(self, request):
        patient_id = request.path_params['id']
        body = await parse_body(UpdatePatientRequest, request)
        updates = body.model_dump(exclude_none=True)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            if not await fd.get_patient(patient_id):
                return not_found('Patient not found')
            if updates:
                await fd.update_patient(patient_id, updates)
            row = await fd.get_patient(patient_id)
            await AuditLog(conn).log_event(
                event_type='frontdesk.patient_updated',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=row['id'],
                details={'patient_id': patient_id, 'updates': updates},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': _row_dict(row)})


class RisPatientInsuranceHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_WRITE)
    async def post(self, request):
        patient_id = request.path_params['id']
        body = await parse_body(CreateInsuranceRequest, request)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            patient = await fd.get_patient(patient_id)
            if not patient:
                return not_found('Patient not found')
            row = await fd.create_insurance({
                'patient_id': patient_id,
                'policy_number': body.policy_number,
                'guarantor_name': body.guarantor_name,
                'authorization_status': body.authorization_status,
                'authorization_number': body.authorization_number,
                'notes': body.notes,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='frontdesk.insurance_created',
                actor_id=request.user.id,
                resource_type='insurance',
                resource_id=row['id'],
                details={'patient_id': patient_id},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})


class RisPatientCheckInHandler(HTTPEndpoint):
    # F-09: The Visits UI performs check-in via PUT /visits/{id} (REGISTRATION_WRITE),
    # not this endpoint. Both permissions are held by receptionists. This endpoint
    # is kept on SCHEDULE_WRITE for backend/machine-to-machine callers (HL7, RIS)
    # that may not hold REGISTRATION_WRITE.
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        patient_id = request.path_params['id']
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            if not await fd.get_patient(patient_id):
                return not_found('Patient not found')
            visit = await fd.find_open_visit(patient_id)
            if not visit:
                return api_error(
                    'NO_OPEN_VISIT',
                    'Patient has no open visit to check in',
                    status=409,
                )
            await fd.update_visit(visit['id'], {'status': 'checked_in'})
            row = dict(visit)
            row['status'] = 'checked_in'
            await AuditLog(conn).log_event(
                event_type='frontdesk.checkin',
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=visit['id'],
                details={'patient_id': patient_id},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': _row_dict(row)})


class VisitsHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        date_str = request.query_params.get('date')
        # Clamp pagination like users.py: oversized/negative page and
        # per_page must not reach the SQL (they are interpolated into the
        # query); non-numeric values are a client error, not a 500.
        try:
            page = int(request.query_params.get('page', '1'))
            per_page = int(request.query_params.get('per_page', '20'))
        except (TypeError, ValueError):
            return validation_error('Invalid pagination parameters')
        page = max(1, page)
        per_page = max(1, min(200, per_page))
        async with get_conn() as conn:
            rows, total = await FrontDesk(conn).list_visits(
                status=status, date=date_str, page=page, per_page=per_page,
            )
        return ok({
            'data': [_row_dict(r) for r in rows],
            'total': total,
            'page': page,
            'per_page': per_page,
        })

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        body = await parse_body(CreateVisitRequest, request)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            row = await fd.create_visit({
                'patient_id': body.patient_id,
                'visit_date': body.visit_date,
                'destination_room': body.destination_room,
                'status': 'registered',
                'hl7_sync_status': 'pending',
                'created_by': str(request.user.id),
            })
            await fd.seed_default_consents(row['id'])
            await AuditLog(conn).log_event(
                event_type='frontdesk.visit_created',
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=row['id'],
                details={'patient_id': body.patient_id, 'destination_room': body.destination_room or ''},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})


class VisitHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        visit_id = request.path_params['id']
        async with get_conn() as conn:
            row = await FrontDesk(conn).get_visit(visit_id)
        if not row:
            return not_found('Visit not found')
        return ok({'data': _row_dict(row)})

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def put(self, request):
        visit_id = request.path_params['id']
        body = await parse_body(UpdateVisitRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            existing = await FrontDesk(conn).get_visit(visit_id)
            if not existing:
                return not_found('Visit not found')
            # R5-10: one canonical lifecycle — a visit moves strictly forward
            # registered → checked_in → in_progress → complete, and nothing
            # leaves 'complete'. Illegal transitions are rejected (409) so a
            # REGISTRATION_WRITE caller can never skip check-in or resurrect
            # a finished visit; same-status no-ops stay idempotent.
            new_status = updates.get('status')
            if new_status and new_status != existing['status']:
                allowed = _VISIT_TRANSITIONS.get(existing['status'], set())
                if new_status not in allowed:
                    return api_error(
                        'INVALID_VISIT_TRANSITION',
                        f'Visit cannot transition {existing["status"]} -> {new_status}',
                        status=409,
                    )
            await FrontDesk(conn).update_visit(visit_id, updates)
            event_type = 'frontdesk.checkin' if updates.get('status') == 'checked_in' else 'frontdesk.visit_updated'
            await AuditLog(conn).log_event(
                event_type=event_type,
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=visit_id,
                details=updates,
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class VisitOrdersHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        visit_id = request.path_params['id']
        async with get_conn() as conn:
            visit = await FrontDesk(conn).get_visit(visit_id)
            if not visit:
                return not_found('Visit not found')
            rows = await FrontDesk(conn).list_orders(visit_id)
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        visit_id = request.path_params['id']
        body = await parse_body(CreateOrderRequest, request)
        async with get_conn() as conn:
            visit = await FrontDesk(conn).get_visit(visit_id)
            if not visit:
                return not_found('Visit not found')
            row = await FrontDesk(conn).create_order({
                'visit_id': visit_id,
                'patient_id': visit['patient_id'],
                'requested_procedure': body.requested_procedure,
                'indication': body.indication,
                'urgency': body.urgency,
                'referring_physician': body.referring_physician,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='frontdesk.order_created',
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=visit_id,
                details={'requested_procedure': body.requested_procedure, 'urgency': body.urgency},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})


class AppointmentAvailabilityHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        modality = request.query_params.get('modality') or ''
        date_str = request.query_params.get('date') or ''
        try:
            day = date.fromisoformat(date_str) if date_str else date.today()
        except ValueError:
            return validation_error('Invalid date')

        slots = [time(h, m) for h in range(8, 18) for m in (0, 30)]
        async with get_conn() as conn:
            # R5-16: unconfigured capacity must be loud, not silent — a
            # modality with no capacity row previously booked at capacity 1
            # with a full grid. 404 surfaces "not configured" to the caller.
            capacity = await FrontDesk(conn).get_capacity(modality, day.weekday())
            if capacity is None and modality:
                return not_found('Modality not configured for this day')
            capacity = capacity or 1
            appt_rows = await conn.fetch(
                """
                SELECT scheduled_time, COUNT(1) AS c FROM appointments
                WHERE modality = $1 AND scheduled_date = $2 AND status != 'cancelled'
                GROUP BY scheduled_time
                """,
                modality, day,
            )

        # Appointments are the single source of truth for booked capacity
        # (R5-01) — the mirrored worklist entry is not counted again.
        booked = {}
        for r in appt_rows:
            key = _slot_key(r['scheduled_time'])
            booked[key] = booked.get(key, 0) + r['c']

        data = []
        for s in slots:
            key = _slot_key(s)
            n = booked.get(key, 0)
            data.append({
                'time': key,
                'capacity': capacity,
                'booked': n,
                'state': 'full' if n >= capacity else 'free',
            })
        return ok({'data': data})


class AppointmentsHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_READ)
    async def get(self, request):
        date_str = request.query_params.get('date')
        date_val = None
        if date_str:
            try:
                date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                date_val = None
        modality = request.query_params.get('modality')
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            rows = await FrontDesk(conn).list_appointments(
                date=date_val, modality=modality, patient_id=patient_id,
            )
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateAppointmentRequest, request)
        lock_key = zlib.crc32(
            f'{body.modality}|{body.scheduled_date}|{body.scheduled_time}'.encode(),
        )
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            # Conflict check + inserts run in one transaction so two concurrent
            # bookings can never double-book a slot below capacity. The
            # advisory lock serializes competing bookings of the same slot
            # across connections (R3-03) — locking the capacity row would be a
            # no-op on days where no modality_capacity row exists.
            async with conn.transaction():
                await conn.execute('SELECT pg_advisory_xact_lock($1::bigint)', lock_key)
                # R5-16: bookings against an unconfigured modality must not
                # silently succeed at capacity 1 — same 404 as availability.
                capacity = await fd.get_capacity(body.modality, body.scheduled_date.weekday())
                if capacity is None and body.modality:
                    return not_found('Modality not configured for this day')
                capacity = capacity or 1
                booked = await fd.count_slot_booked(
                    body.modality, body.scheduled_date, body.scheduled_time,
                ) or 0
                if booked >= capacity:
                    return api_error(
                        'SLOT_CONFLICT', 'Slot already booked — availability refreshed', status=409,
                    )
                patient = await fd.get_patient(body.patient_id)
                if not patient:
                    # Never schedule against a phantom patient (R5-06) —
                    # neither the appointment nor the worklist entry is
                    # created, so the modality worklist stays clean.
                    return not_found('Patient not found')
                wl_id = await fd.create_worklist_entry({
                    'patient_id': body.patient_id,
                    'patient_name': patient['name'],
                    'patient_birth_date': patient['birth_date'],
                    'patient_sex': patient['sex'],
                    'scheduled_date': body.scheduled_date,
                    'scheduled_time': body.scheduled_time,
                    'modality': body.modality,
                    'station_ae_title': body.room,
                    'created_by': str(request.user.id),
                })
                appt = await fd.create_appointment({
                    'patient_id': body.patient_id,
                    'visit_id': body.visit_id,
                    'worklist_entry_id': wl_id,
                    'modality': body.modality,
                    'room': body.room,
                    'technologist': body.technologist,
                    'scheduled_date': body.scheduled_date,
                    'scheduled_time': body.scheduled_time,
                    'created_by': str(request.user.id),
                })
                await AuditLog(conn).log_event(
                    event_type='frontdesk.appointment_created',
                    actor_id=request.user.id,
                    resource_type='appointment',
                    resource_id=appt['id'],
                    details={'patient_id': body.patient_id, 'modality': body.modality},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
        return created({'data': _row_dict(appt)})


class AppointmentHandler(HTTPEndpoint):
    @requires_permission(Permission.SCHEDULE_WRITE)
    async def delete(self, request):
        appointment_id = request.path_params['id']
        async with get_conn() as conn:
            row = await conn.fetchrow(
                'SELECT id FROM appointments WHERE id = $1', appointment_id,
            )
            if not row:
                return not_found('Appointment not found')
            await FrontDesk(conn).cancel_appointment(appointment_id)
            await AuditLog(conn).log_event(
                event_type='frontdesk.appointment_cancelled',
                actor_id=request.user.id,
                resource_type='appointment',
                resource_id=appointment_id,
                details={},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


class ConsentsHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        visit_id = request.path_params['id']
        async with get_conn() as conn:
            rows = await FrontDesk(conn).list_consents(visit_id)
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        visit_id = request.path_params['id']
        # /visits/{id}/consents/attach is a second POST on this handler —
        # both routes are wired to the same class, distinguished by path.
        if request.url.path.endswith('/attach'):
            body = await parse_body(AttachConsentRequest, request)
            async with get_conn() as conn:
                row = await FrontDesk(conn).attach_consent(
                    visit_id, body.consent_type, body.file_name, str(request.user.id),
                )
                await AuditLog(conn).log_event(
                    event_type='frontdesk.consent_attached',
                    actor_id=request.user.id,
                    resource_type='visit',
                    resource_id=visit_id,
                    details={'consent_type': body.consent_type, 'file_name': body.file_name},
                    tenant=effective_tenant(request),
                    request_id=request_id_var.get(),
                )
            return ok({'data': _row_dict(row)})

        body = await parse_body(CreateConsentRequest, request)
        async with get_conn() as conn:
            row = await FrontDesk(conn).create_consent({
                'visit_id': visit_id,
                'consent_type': body.consent_type,
                'status': body.status or 'attached',
                'file_name': body.file_name,
                'attached_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='frontdesk.consent_created',
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=visit_id,
                details={'consent_type': body.consent_type},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})


class InsuranceHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        patient_id = request.path_params['id']
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            patient = await fd.get_patient(patient_id)
            if not patient:
                return not_found('Patient not found')
            rows = await fd.list_insurance(patient_id)
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        patient_id = request.path_params['id']
        body = await parse_body(CreateInsuranceRequest, request)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            patient = await fd.get_patient(patient_id)
            if not patient:
                return not_found('Patient not found')
            row = await fd.create_insurance({
                'patient_id': patient_id,
                'policy_number': body.policy_number,
                'guarantor_name': body.guarantor_name,
                'authorization_status': body.authorization_status,
                'authorization_number': body.authorization_number,
                'notes': body.notes,
                'created_by': str(request.user.id),
            })
            await AuditLog(conn).log_event(
                event_type='frontdesk.insurance_created',
                actor_id=request.user.id,
                resource_type='insurance',
                resource_id=row['id'],
                details={'patient_id': patient_id},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})

    @requires_permission(Permission.REGISTRATION_WRITE)
    async def put(self, request):
        insurance_id = request.path_params['id']
        body = await parse_body(UpdateInsuranceRequest, request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return ok({})
        async with get_conn() as conn:
            row = await conn.fetchrow(
                'SELECT id FROM insurance_records WHERE id = $1', insurance_id,
            )
            if not row:
                return not_found('Insurance record not found')
            await FrontDesk(conn).update_insurance(insurance_id, updates)
            await AuditLog(conn).log_event(
                event_type='frontdesk.insurance_updated',
                actor_id=request.user.id,
                resource_type='insurance',
                resource_id=insurance_id,
                details=updates,
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({})


# ---- MPI merge / undo (S3-11) ----


class RisPatientsMergeHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_MERGE)
    async def post(self, request):
        body = await parse_body(MergePatientsRequest, request)
        if body.surviving_patient_id == body.merged_patient_id:
            return api_error('SAME_PATIENT', 'Cannot merge a patient with itself', status=400)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            surviving = await fd.get_patient(body.surviving_patient_id)
            if not surviving:
                return not_found('Surviving patient not found')
            merged = await fd.get_patient(body.merged_patient_id)
            if not merged:
                return not_found('Merged patient not found')
            result = await fd.merge_patients(
                body.surviving_patient_id, body.merged_patient_id,
                reason=body.reason or '',
            )
            await AuditLog(conn).log_event(
                event_type='mpi.patient_merged',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=surviving['id'],
                details={
                    'surviving_patient_id': body.surviving_patient_id,
                    'merged_patient_id': body.merged_patient_id,
                    'reason': body.reason or '',
                },
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': result})


class RisPatientsUndoMergeHandler(HTTPEndpoint):
    @requires_permission(Permission.PATIENT_MERGE)
    async def post(self, request):
        body = await parse_body(UndoMergeRequest, request)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            patient = await fd.get_patient(body.patient_id)
            if not patient:
                return not_found('Patient not found')
            result = await fd.undo_merge(body.patient_id, reason=body.reason or '')
            await AuditLog(conn).log_event(
                event_type='mpi.patient_unmerged',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=patient['id'],
                details={'patient_id': body.patient_id, 'reason': body.reason or ''},
                tenant=effective_tenant(request),
                request_id=request_id_var.get(),
            )
        return ok({'data': result})


# ---- Insurance eligibility (S3-14 / FD-02) ----


class RisPatientEligibilityHandler(HTTPEndpoint):
    """FD-02: return coverage data from the patient's most recent insurance
    record — provider, member ID, copay, deductible, coverage status.

    No live payer API is integrated; eligibility is derived from the stored
    policy (the payer verification adapter is a later-phase concern).
    A patient with no recorded policy reports status 'none'."""

    @requires_permission(Permission.PATIENT_READ)
    async def get(self, request):
        patient_id = request.path_params['id']
        from datetime import datetime, timezone
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            patient = await fd.get_patient(patient_id)
            if not patient:
                return not_found('Patient not found')
            records = await fd.list_insurance(patient_id)
        record = records[0] if records else None
        if record is None:
            return ok({
                'data': {
                    'patient_id': patient_id,
                    'status': 'none',
                    'provider': '',
                    'member_id': '',
                    'copay_amount': None,
                    'deductible_total': None,
                    'deductible_remaining': None,
                    'checked_at': datetime.now(timezone.utc).isoformat(),
                },
            })
        return ok({
            'data': {
                'patient_id': patient_id,
                'status': 'active',
                'provider': record.get('provider') or '',
                'member_id': record.get('member_id') or '',
                'copay_amount': record.get('copay_amount'),
                'deductible_total': record.get('deductible_total'),
                'deductible_remaining': record.get('deductible_remaining'),
                'checked_at': datetime.now(timezone.utc).isoformat(),
            },
        })


class WaitingQueueHandler(HTTPEndpoint):
    @requires_permission(Permission.QUEUE_READ)
    async def get(self, request):
        date_str = request.query_params.get('date') or ''
        async with get_conn() as conn:
            rows = await FrontDesk(conn).waiting_queue(date=date_str)
        # HIPAA minimum necessary: initials + last-4 of the MRN only —
        # full names and MRNs never leave the server.
        data = []
        for r in rows:
            name = r['patient_name'] or ''
            pid = r['patient_id'] or ''
            initials = ''.join(w[0].upper() + '.' for w in name.split() if w) if name else ''
            last4 = pid[-4:] if len(pid) >= 4 else pid
            data.append({
                'visit_id': str(r['visit_id']),
                'initials': initials,
                'last4': last4,
                'status': r['status'],
                'destination': r['destination'] or '',
                'updated_at': str(r['updated_at']),
                # FD-05: minutes-since-arrival (None for registered-only visits).
                'wait_minutes': (round(r['wait_minutes'])
                                 if r.get('wait_minutes') is not None
                                 else None),
            })
        return ok({'data': data})
