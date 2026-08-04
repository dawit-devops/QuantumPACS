"""Front Desk (R08) endpoints — patient registration, visits, order intake,
appointment scheduling with capacity conflict detection, consent capture,
insurance/guarantor records and the privacy-projected waiting queue.

All mutations are audit-logged; the waiting queue applies HIPAA minimum
necessary projection (initials + last-4 of MRN, never full names).
"""
import time as _time
import uuid
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
    CreateVisitRequest, UpdateInsuranceRequest, UpdateVisitRequest,
)
from db.audit_log import AuditLog
from db.conn import get_conn
from db.frontdesk import FrontDesk
from log import request_id_var


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


class PatientsSearchHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return ok({'data': []})
        async with get_conn() as conn:
            rows = await FrontDesk(conn).search_patients(q)
        return ok({'data': [_row_dict(r) for r in rows]})


class PatientsRegistrationHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_WRITE)
    async def post(self, request):
        body = await parse_body(CreatePatientRequest, request)
        patient_id = (body.patient_id or '').strip() or f'P{int(_time.time() * 1000)}'
        async with get_conn() as conn:
            try:
                row = await FrontDesk(conn).create_patient({
                    'patient_id': patient_id,
                    'name': body.name,
                    'birth_date': body.birth_date,
                    'sex': body.sex,
                    'meta': body.meta,
                })
            except UniqueViolationError:
                return validation_error('Patient with this ID already exists')
            await AuditLog(conn).log_event(
                event_type='frontdesk.patient_registered',
                actor_id=request.user.id,
                resource_type='patient',
                resource_id=row['id'],
                details={'patient_id': patient_id},
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return created({'data': _row_dict(row)})


class VisitsHandler(HTTPEndpoint):
    @requires_permission(Permission.REGISTRATION_READ)
    async def get(self, request):
        status = request.query_params.get('status')
        date_str = request.query_params.get('date')
        page = int(request.query_params.get('page', '1'))
        per_page = int(request.query_params.get('per_page', '20'))
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
                tenant=request.user.tenant,
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
            await FrontDesk(conn).update_visit(visit_id, updates)
            event_type = 'frontdesk.checkin' if updates.get('status') == 'checked_in' else 'frontdesk.visit_updated'
            await AuditLog(conn).log_event(
                event_type=event_type,
                actor_id=request.user.id,
                resource_type='visit',
                resource_id=visit_id,
                details=updates,
                tenant=request.user.tenant,
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
                tenant=request.user.tenant,
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
            capacity = await FrontDesk(conn).get_capacity(modality, day.weekday()) or 1
            appt_rows = await conn.fetch(
                """
                SELECT scheduled_time, COUNT(1) AS c FROM appointments
                WHERE modality = $1 AND scheduled_date = $2 AND status != 'cancelled'
                GROUP BY scheduled_time
                """,
                modality, day,
            )
            wl_rows = await conn.fetch(
                """
                SELECT scheduled_time, COUNT(1) AS c FROM worklist_entries
                WHERE modality = $1 AND scheduled_date = $2 AND status = 'scheduled'
                GROUP BY scheduled_time
                """,
                modality, day,
            )

        booked = {}
        for rows in (appt_rows, wl_rows):
            for r in rows:
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
        modality = request.query_params.get('modality')
        patient_id = request.query_params.get('patient_id')
        async with get_conn() as conn:
            rows = await FrontDesk(conn).list_appointments(
                date=date_str, modality=modality, patient_id=patient_id,
            )
        return ok({'data': [_row_dict(r) for r in rows]})

    @requires_permission(Permission.SCHEDULE_WRITE)
    async def post(self, request):
        body = await parse_body(CreateAppointmentRequest, request)
        async with get_conn() as conn:
            fd = FrontDesk(conn)
            # Conflict check + inserts run in one transaction so two concurrent
            # bookings can never double-book a slot below capacity.
            async with conn.transaction():
                capacity = await fd.get_capacity(body.modality, body.scheduled_date.weekday()) or 1
                booked = await fd.count_slot_booked(
                    body.modality, body.scheduled_date, body.scheduled_time,
                ) or 0
                if booked >= capacity:
                    return api_error(
                        'SLOT_CONFLICT', 'Slot already booked — availability refreshed', status=409,
                    )
                patient = await fd.get_patient(body.patient_id)
                appt = await fd.create_appointment({
                    'patient_id': body.patient_id,
                    'visit_id': body.visit_id,
                    'modality': body.modality,
                    'room': body.room,
                    'technologist': body.technologist,
                    'scheduled_date': body.scheduled_date,
                    'scheduled_time': body.scheduled_time,
                    'created_by': str(request.user.id),
                })
                wl_id = await fd.create_worklist_entry({
                    'patient_id': body.patient_id,
                    'patient_name': patient['name'] if patient else '',
                    'patient_birth_date': patient['birth_date'] if patient else '',
                    'patient_sex': patient['sex'] if patient else '',
                    'scheduled_date': body.scheduled_date,
                    'scheduled_time': body.scheduled_time,
                    'modality': body.modality,
                    'station_ae_title': body.room,
                    'created_by': str(request.user.id),
                })
                await AuditLog(conn).log_event(
                    event_type='frontdesk.appointment_created',
                    actor_id=request.user.id,
                    resource_type='appointment',
                    resource_id=appt['id'],
                    details={'patient_id': body.patient_id, 'modality': body.modality},
                    tenant=request.user.tenant,
                    request_id=request_id_var.get(),
                )
        return created({'data': {**_row_dict(appt), 'worklist_entry_id': str(wl_id)}})


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
                tenant=request.user.tenant,
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
                    tenant=request.user.tenant,
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
                tenant=request.user.tenant,
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
                tenant=request.user.tenant,
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
                tenant=request.user.tenant,
                request_id=request_id_var.get(),
            )
        return ok({})


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
            initials = ' '.join(w[0].upper() + '.' for w in name.split() if w) if name else ''
            last4 = pid[-4:] if len(pid) >= 4 else pid
            data.append({
                'visit_id': str(r['visit_id']),
                'initials': initials,
                'last4': last4,
                'status': r['status'],
                'destination': r['destination'] or '',
                'updated_at': str(r['updated_at']),
            })
        return ok({'data': data})
