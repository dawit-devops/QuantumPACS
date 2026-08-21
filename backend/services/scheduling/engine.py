"""Scheduling engine (S4-10) — conflict-free booking + availability.

Deep module: the whole booking pipeline (conflict check, schedule-window
validation, order transition, audit) hides behind book() and
available_slots(). Conflict-free is guaranteed twice — the engine
pre-checks overlaps for a friendly error, and the no_double_book EXCLUDE
constraint (migration 069) is the DB-level backstop under concurrency.

Repos are constructor-injected (default: built from the request conn);
injected repos skip DB access entirely, which is how unit tests exercise
the decision logic without a pool.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from config import config as _config
from db.conn import get_conn


class SchedulingConflict(Exception):
    """The requested slot is not bookable (overlap or outside availability)."""


class SchedulingNotFound(Exception):
    """A referenced entity (order/resource/appointment/patient) does not exist.

    Raised instead of ValueError so the API layer can answer 404 — a
    missing reference is a not-found outcome, not a server fault.
    """


class SchedulingValidation(Exception):
    """Malformed scheduling input (bad ISO datetime, empty id)."""


class SchedulingEngine:
    def __init__(self, actor_id='system', appointments=None,
                 schedules=None, lifecycle=None, orders=None,
                 contraindications=None, audit=None, worklist=None,
                 resources=None, patients=None):
        self.actor_id = actor_id
        self._appointments = appointments
        self._schedules = schedules
        self._lifecycle = lifecycle
        self._orders = orders
        self._audit = audit
        self._worklist = worklist
        self._resources = resources
        self._patients = patients
        # Injectable async checker: order_id -> list[str] of contraindication
        # reasons. None = no contraindication gate (default behaviour).
        self._contraindication_check = contraindications

    async def _open(self):
        """Yield a conn only when repos were not injected (production path)."""
        if (self._appointments or self._schedules or self._lifecycle
                or self._orders or self._contraindication_check
                or self._worklist or self._resources or self._patients):
            yield None
            return
        cm = get_conn()
        conn = await cm.__aenter__()
        try:
            yield conn
        finally:
            await cm.__aexit__(None, None, None)

    def _repos(self, conn):
        from db.ris_appointments import RisAppointments
        from db.ris_orders import RisOrders
        from db.ris_resources import RisResourceSchedules
        from db.patient import Patient
        from services.order_lifecycle.service import OrderLifecycleService
        return (
            self._appointments or RisAppointments(conn),
            self._schedules or RisResourceSchedules(conn),
            self._lifecycle or OrderLifecycleService(conn),
            self._orders or RisOrders(conn),
            self._patients or Patient(conn),
        )

    @staticmethod
    def _slot_within_windows(start: datetime, end: datetime, windows) -> bool:
        day = start.weekday()
        for w in windows:
            if w['day_of_week'] != day:
                continue
            win_start = time.fromisoformat(str(w['start_time']))
            win_end = time.fromisoformat(str(w['end_time']))
            if win_start <= start.time() and end.time() <= win_end:
                return True
        return False

    async def book(self, *, order_id, patient_id, resource_id,
                   start_time, end_time, reason='', override_reason=''):
        start = _as_datetime(start_time)
        end = _as_datetime(end_time)
        if end <= start:
            raise SchedulingConflict('end_time must be after start_time')

        async for conn in self._open():
            appointments, schedules, lifecycle, orders, patients = self._repos(conn)

            # Order-less booking (scheduler types a patient ID directly):
            # no order gates apply, no lifecycle/worklist hand-off. The
            # appointment still audits and enforces availability/conflicts.
            order = None
            if order_id:
                order = await orders.get(order_id)
                if order is None:
                    raise SchedulingNotFound(
                        f'Order {order_id} not found for scheduling')

                # F-02: order.patient_id must match booking patient_id —
                # otherwise the appointment and the order refer to different
                # patients, causing a wrong-patient scheduling event.
                if order.get('patient_id') != patient_id:
                    raise SchedulingConflict(
                        'order.patient_id and booking patient_id must match')

                # Prior-authorization gate (R2-01-05): orders that need auth
                # cannot be booked until APPROVED. An override_reason audited
                # bypass exists for expedited cases (e.g. verbal payer approval,
                # patient prepaid, emergency).
                # C-7: EXPIRED auth is as un-bookable as PENDING/DENIED —
                # the prior auth lapsed, so the slot must not be taken.
                pa = order.get('prior_auth_status', 'NOT_REQUIRED')
                if pa in ('REQUIRED', 'PENDING', 'DENIED', 'EXPIRED'):
                    if override_reason:
                        await self._audit_log(conn).log_event(
                            'PRIOR_AUTH_OVERRIDE', self.actor_id,
                            'ris_orders', order_id,
                            details={'reason': override_reason, 'prior_auth_status': pa})
                    else:
                        raise SchedulingConflict(
                            f'Order {order_id} requires prior authorization ({pa})')

                # Contraindication gate: injectable checker; default off.
                if self._contraindication_check is not None:
                    reasons = await self._contraindication_check(order_id)
                    if reasons:
                        raise SchedulingConflict('; '.join(reasons))

            # F-02: order-less booking must verify the patient exists
            # (R5-06). A scheduler typing a MRN directly cannot create an
            # appointment against a phantom patient.
            if not order_id:
                patients = self._patients
                if patients is not None:
                    patient = await patients.get_by_mrn(patient_id)
                    if patient is None:
                        raise SchedulingNotFound(
                            f'Patient {patient_id} not found')

            # B-7: an unknown resource must be a clean not-found before any
            # availability/conflict work — otherwise the FK on insert turns
            # it into a ForeignKeyViolationError (500). Skipped when repos
            # are injected (unit mode): the injected tests own the lookup.
            if conn is not None or self._resources is not None:
                from db.ris_resources import RisResources
                resource_row = await (self._resources or RisResources(conn)).get(
                    resource_id)
                if resource_row is None:
                    raise SchedulingNotFound(
                        f'Resource {resource_id} not found')

            windows = await schedules.for_resource(resource_id)
            if windows and not self._slot_within_windows(start, end, windows):
                raise SchedulingConflict(
                    f'Slot outside availability for resource {resource_id}')

            existing = await appointments.for_resource(resource_id, start, end)
            # F-08: whitespace-only override must collapse to '' so a
            # scheduler cannot bypass the mandatory-reason audit gate.
            override_reason = (override_reason or '').strip()

            # H3: all mutations below (cancelled/override deletes, audit,
            # insert, order transition) must be atomic — a failed rebook must
            # roll back the deletes (proven real-DB in TestOverrideAtomicity).
            # Injected-repo mode (conn is None) has no transaction to join.
            from contextlib import AsyncExitStack
            async with AsyncExitStack() as stack:
                if conn is not None:
                    await stack.enter_async_context(conn.transaction())

                # F-03: CANCELLED appointments do not occupy capacity. Separate
                # them from active conflicts — they are physically removed
                # (released) without requiring an override reason.
                cancelled = [a for a in existing if a.get('status') == 'CANCELLED']
                active = [a for a in existing if a.get('status') != 'CANCELLED']

                # Release cancelled slots (audit lives in audit_log, not the row)
                for appt in cancelled:
                    await appointments.delete(appt['id'])

                overrode = []
                bumped_order_ids = []
                if active:
                    if not override_reason:
                        raise SchedulingConflict(
                            f'Resource {resource_id} already booked '
                            f'{start.isoformat()}–{end.isoformat()}')
                    # Override: mandatory reason, audited; the EXCLUDE constraint
                    # cannot express "only CANCELLED" so the conflicting rows are
                    # physically removed before the new booking.
                    overrode = [str(a['id']) for a in active]
                    bumped_order_ids = [
                        str(a['order_id']) for a in active if a.get('order_id')]
                    for appt in active:
                        await appointments.delete(appt['id'])
                    await self._audit_log(conn).log_event(
                        'APPOINTMENT_OVERRIDE', self.actor_id,
                        'ris_appointments', resource_id,
                        details={'overrode': overrode, 'reason': override_reason})

                try:
                    row = await appointments.create({
                        'order_id': order_id or None,
                        'resource_id': resource_id,
                        'patient_id': patient_id,
                        'start_time': start,
                        'end_time': end,
                        'reason': reason,
                        'override_reason': override_reason if overrode else '',
                        'created_by': self.actor_id,
                    })
                except Exception as exc:
                    # H2: the pre-check and the EXCLUDE constraint race — two
                    # concurrent bookings can both pass for_resource() and one
                    # then hits the GiST backstop. That is the same business
                    # outcome as the pre-check conflict; surface it as a 409,
                    # never a 500.
                    from asyncpg.exceptions import ExclusionViolationError
                    if isinstance(exc, ExclusionViolationError):
                        raise SchedulingConflict(
                            f'Resource {resource_id} already booked '
                            f'{start.isoformat()}–{end.isoformat()}') from exc
                    raise

                if not order:
                    # Order-less booking: nothing to transition or hand off — the
                    # appointment is the record (a later order may be linked via
                    # reschedule/update endpoints, none exist yet).
                    await self._audit_log(conn).log_event(
                        'APPOINTMENT_BOOKED', self.actor_id,
                        'ris_appointments', row['id'],
                        {'order_id': None, 'resource_id': resource_id,
                         'start_time': str(start), 'end_time': str(end),
                         'reason': reason})
                    return dict(row)

                # ORDERED -> SCHEDULED is the only valid transition out of
                # ORDERED (lifecycle service enforces + audits).
                updated = await lifecycle.transition(
                    order_id, 'SCHEDULED', self.actor_id, reason)
                if updated is None:
                    # Order vanished mid-booking — appointment must not outlive it.
                    await appointments.delete(row['id'])
                    raise ValueError(f'Order {order_id} not found for scheduling')

                # Best-effort worklist hand-off: the MWL/MPPS flow reads
                # scheduled exams from worklist_entries, so a booking must
                # appear there. A failure is audited, never rolled back — the
                # appointment is the source of truth.
                if self._worklist is not None or conn is not None:
                    from db.ris_resources import RisResources
                    from db.worklist import Worklist
                    worklist = self._worklist or Worklist(conn)
                    resource = await (self._resources or RisResources(conn)).get(
                        resource_id)
                    start_dt = _as_datetime(row['start_time'])

                    # H5: orders bumped by an override must leave the MWL — a
                    # displaced patient's exam must not run against the new
                    # booking's slot.
                    for bumped_id in bumped_order_ids:
                        await self._cancel_order_worklist(
                            worklist, orders, bumped_id, row['id'], conn)

                    accession = order.get('accession_number', '')
                    if accession:
                        try:
                            entry = await worklist.get_by_accession(accession)
                            data = {
                                'patient_id': order['patient_id'],
                                'patient_name': order.get('patient_name', ''),
                                'accession_number': accession,
                                'scheduled_date': start_dt.date(),
                                'scheduled_time': start_dt.time(),
                                'modality': (resource or {}).get('modality', ''),
                                'status': 'scheduled',
                                # S6-23: the order's priority (STAT/URGENT/
                                # ROUTINE) must flow into the MWL so the
                                # tracking board can sort STAT first.
                                'requested_procedure_priority':
                                    order.get('priority', ''),
                                'created_by': self.actor_id,
                            }
                            if entry:
                                # H5: re-booking the same order must not
                                # duplicate its MWL entry.
                                await worklist.update_entry(entry['id'], data)
                            else:
                                await worklist.create(data)
                        except Exception as exc:
                            await self._audit_log(conn).log_event(
                                'WORKLIST_CREATE_FAILED', self.actor_id,
                                'ris_appointments', row['id'],
                                details={'accession': accession,
                                         'error': str(exc)})

                # B-4: the order timeline (audit log) must carry the booking
                # itself — resource, slot and reason — not just the lifecycle
                # transition. The UI shows "booked CT Room 1 09:00–09:30".
                await self._audit_log(conn).log_event(
                    'APPOINTMENT_BOOKED', self.actor_id,
                    'ris_appointments', row['id'],
                    {'order_id': str(order_id), 'resource_id': resource_id,
                     'start_time': str(start), 'end_time': str(end),
                     'reason': reason})
                return dict(row)

    async def _cancel_order_worklist(self, worklist, orders, order_id,
                                     audit_target, conn=None):
        """Best-effort MWL removal for a bumped/cancelled order."""
        try:
            order = await orders.get(order_id)
            accession = (order or {}).get('accession_number', '')
            if not accession:
                return
            entry = await worklist.get_by_accession(accession)
            if entry:
                await worklist.cancel(entry['id'])
        except Exception as exc:
            await self._audit_log(conn).log_event(
                'WORKLIST_CANCEL_FAILED', self.actor_id,
                'ris_appointments', audit_target,
                details={'order_id': str(order_id), 'error': str(exc)})

    def _audit_log(self, conn):
        if self._audit is not None:
            return self._audit
        from db.audit_log import AuditLog
        return AuditLog(conn)

    async def reschedule(self, *, appointment_id, new_start_time,
                         new_end_time, reason=''):
        start = _as_datetime(new_start_time)
        end = _as_datetime(new_end_time)
        if end <= start:
            raise SchedulingConflict('end_time must be after start_time')

        async for conn in self._open():
            appointments, schedules, _, orders, _ = self._repos(conn)
            current = await appointments.get(appointment_id)
            if current is None:
                raise SchedulingNotFound(
                    f'Appointment {appointment_id} not found')

            # Same gate as booking: the new slot must be inside availability
            # and free (ignoring the appointment's own current slot).
            windows = await schedules.for_resource(current['resource_id'])
            if windows and not self._slot_within_windows(start, end, windows):
                raise SchedulingConflict(
                    f'Slot outside availability for resource {current["resource_id"]}')
            existing = await appointments.for_resource(
                current['resource_id'], start, end)
            existing = [a for a in existing
                        if str(a['id']) != str(appointment_id)]
            # H4: CANCELLED appointments do not occupy capacity — same F-03
            # semantics as book(). The EXCLUDE constraint cannot express the
            # filter, so cancelled rows blocking the target slot are released
            # (physically removed) instead of rejecting the reschedule.
            cancelled = [a for a in existing if a.get('status') == 'CANCELLED']
            active = [a for a in existing if a.get('status') != 'CANCELLED']
            if active:
                raise SchedulingConflict(
                    f'Resource {current["resource_id"]} already booked '
                    f'{start.isoformat()}–{end.isoformat()}')
            for appt in cancelled:
                await appointments.delete(appt['id'])

            # H3: the release + update + audit are atomic.
            from contextlib import AsyncExitStack
            async with AsyncExitStack() as stack:
                if conn is not None:
                    await stack.enter_async_context(conn.transaction())
                row = await appointments.update_slot(
                    appointment_id, start, end, reason)
                await self._audit_log(conn).log_event(
                    'APPOINTMENT_RESCHEDULED', self.actor_id,
                    'ris_appointments', appointment_id,
                    details={'from': str(current['start_time']),
                             'to': str(start), 'reason': reason})

                # H5: the MWL entry moves with the appointment.
                if (current.get('order_id')
                        and (self._worklist is not None or conn is not None)):
                    from db.worklist import Worklist
                    worklist = self._worklist or Worklist(conn)
                    try:
                        order = await orders.get(current['order_id'])
                        accession = (order or {}).get('accession_number', '')
                        entry = None
                        if accession:
                            entry = await worklist.get_by_accession(accession)
                        if entry:
                            await worklist.update_entry(entry['id'], {
                                'scheduled_date': start.date(),
                                'scheduled_time': start.time(),
                            })
                    except Exception as exc:
                        await self._audit_log(conn).log_event(
                            'WORKLIST_UPDATE_FAILED', self.actor_id,
                            'ris_appointments', appointment_id,
                            details={'order_id': str(current['order_id']),
                                     'error': str(exc)})
                return dict(row)

    async def cancel(self, *, appointment_id, reason=''):
        async for conn in self._open():
            appointments, _, lifecycle, orders, _ = self._repos(conn)
            current = await appointments.get(appointment_id)
            if current is None:
                raise SchedulingNotFound(
                    f'Appointment {appointment_id} not found')

            row = await appointments.update_status(appointment_id, 'CANCELLED')
            if current.get('order_id'):
                # SCHEDULED -> CANCELLED is the valid lifecycle transition.
                await lifecycle.transition(
                    current['order_id'], 'CANCELLED', self.actor_id, reason)
                # H5: a cancelled exam must leave the modality worklist.
                if self._worklist is not None or conn is not None:
                    from db.worklist import Worklist
                    worklist = self._worklist or Worklist(conn)
                    await self._cancel_order_worklist(
                        worklist, orders, current['order_id'], appointment_id,
                        conn)
            await self._audit_log(conn).log_event(
                'APPOINTMENT_CANCELLED', self.actor_id,
                'ris_appointments', appointment_id, details={'reason': reason})
            return dict(row)

    async def available_slots(self, *, resource_id, day, slot_minutes=30,
                              day_start='08:00:00', day_end='17:00:00'):
        """Free slot windows for one resource on one day, minus booked ranges."""
        day = _as_date(day)
        # B-10: the availability band is clinic-local time — interpret it
        # in the clinic's configured zone, not UTC.
        tz = ZoneInfo(_config.get('clinic_timezone', 'UTC'))
        start = datetime.combine(day, time.fromisoformat(day_start), tzinfo=tz)
        end = datetime.combine(day, time.fromisoformat(day_end), tzinfo=tz)

        async for conn in self._open():
            appointments, schedules, _, _, _ = self._repos(conn)
            windows = await schedules.for_resource(resource_id)
            existing = await appointments.for_resource(resource_id, start, end)

        # F-03: CANCELLED appointments do not occupy capacity — filter them
        # out so their slots appear free to the calendar.
        existing = [a for a in existing if a.get('status') != 'CANCELLED']

        window = (day_start, day_end)
        for w in windows:
            if w['day_of_week'] == day.weekday():
                window = (str(w['start_time']), str(w['end_time']))
                break

        ws = datetime.combine(day, time.fromisoformat(window[0]), tzinfo=tz)
        we = datetime.combine(day, time.fromisoformat(window[1]), tzinfo=tz)

        busy = []
        for a in existing:
            a_start = _as_datetime(a['start_time'])
            a_end = _as_datetime(a['end_time'])
            busy.append((max(ws, a_start), min(we, a_end)))
        busy = [b for b in busy if b[0] < b[1]]
        busy.sort()

        slots = []
        cursor = ws
        for b_start, b_end in busy:
            while cursor + timedelta(minutes=slot_minutes) <= b_start:
                slots.append({
                    'start': cursor.strftime('%H:%M'),
                    'end': (cursor + timedelta(minutes=slot_minutes)).strftime('%H:%M'),
                })
                cursor += timedelta(minutes=slot_minutes)
            cursor = max(cursor, b_end)
        while cursor + timedelta(minutes=slot_minutes) <= we:
            slots.append({
                'start': cursor.strftime('%H:%M'),
                'end': (cursor + timedelta(minutes=slot_minutes)).strftime('%H:%M'),
            })
            cursor += timedelta(minutes=slot_minutes)
        return slots


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError as exc:
        raise SchedulingValidation(
            f'Invalid datetime {value!r}: expected ISO 8601') from exc


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return _as_datetime(value).date()