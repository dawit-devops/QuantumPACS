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

from datetime import date, datetime, time, timedelta, timezone

from db.conn import get_conn


class SchedulingConflict(Exception):
    """The requested slot is not bookable (overlap or outside availability)."""


class SchedulingEngine:
    def __init__(self, actor_id='system', appointments=None,
                 schedules=None, lifecycle=None, orders=None,
                 contraindications=None, audit=None, worklist=None,
                 resources=None):
        self.actor_id = actor_id
        self._appointments = appointments
        self._schedules = schedules
        self._lifecycle = lifecycle
        self._orders = orders
        self._audit = audit
        self._worklist = worklist
        self._resources = resources
        # Injectable async checker: order_id -> list[str] of contraindication
        # reasons. None = no contraindication gate (default behaviour).
        self._contraindication_check = contraindications

    async def _open(self):
        """Yield a conn only when repos were not injected (production path)."""
        if (self._appointments or self._schedules or self._lifecycle
                or self._orders or self._contraindication_check
                or self._worklist or self._resources):
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
        from services.order_lifecycle.service import OrderLifecycleService
        return (
            self._appointments or RisAppointments(conn),
            self._schedules or RisResourceSchedules(conn),
            self._lifecycle or OrderLifecycleService(conn),
            self._orders or RisOrders(conn),
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
            appointments, schedules, lifecycle, orders = self._repos(conn)

            order = await orders.get(order_id)
            if order is None:
                raise ValueError(f'Order {order_id} not found for scheduling')

            # Prior-authorization gate (S4-10 stub): orders that need auth
            # cannot be booked until APPROVED — visible in the booking form
            # as a warning (RIS-UI-14/15) instead of a silent block.
            pa = order.get('prior_auth_status', 'NOT_REQUIRED')
            if pa in ('REQUIRED', 'PENDING', 'DENIED'):
                raise SchedulingConflict(
                    f'Order {order_id} requires prior authorization ({pa})')

            # Contraindication gate: injectable checker; default off.
            if self._contraindication_check is not None:
                reasons = await self._contraindication_check(order_id)
                if reasons:
                    raise SchedulingConflict('; '.join(reasons))

            windows = await schedules.for_resource(resource_id)
            if windows and not self._slot_within_windows(start, end, windows):
                raise SchedulingConflict(
                    f'Slot outside availability for resource {resource_id}')

            existing = await appointments.for_resource(resource_id, start, end)
            overrode = []
            if existing:
                if not override_reason:
                    raise SchedulingConflict(
                        f'Resource {resource_id} already booked '
                        f'{start.isoformat()}–{end.isoformat()}')
                # Override: mandatory reason, audited; the EXCLUDE constraint
                # cannot express "only CANCELLED" so the conflicting rows are
                # physically removed before the new booking.
                overrode = [str(a['id']) for a in existing]
                for appt in existing:
                    await appointments.delete(appt['id'])
                await self._audit_log(conn).log_event(
                    'APPOINTMENT_OVERRIDE', self.actor_id,
                    'ris_appointments', resource_id,
                    details={'overrode': overrode, 'reason': override_reason})

            row = await appointments.create({
                'order_id': order_id,
                'resource_id': resource_id,
                'patient_id': patient_id,
                'start_time': start,
                'end_time': end,
                'reason': reason,
                'override_reason': override_reason if overrode else '',
                'created_by': self.actor_id,
            })

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
                try:
                    await worklist.create({
                        'patient_id': order['patient_id'],
                        'patient_name': order.get('patient_name', ''),
                        'accession_number': order.get('accession_number', ''),
                        'scheduled_date': start_dt.date(),
                        'scheduled_time': start_dt.time(),
                        'modality': (resource or {}).get('modality', ''),
                        'status': 'scheduled',
                        'created_by': self.actor_id,
                    })
                except Exception as exc:
                    await self._audit_log(conn).log_event(
                        'WORKLIST_CREATE_FAILED', self.actor_id,
                        'ris_appointments', row['id'],
                        details={'error': str(exc)})
            return dict(row)

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
            appointments, schedules, _, _ = self._repos(conn)
            current = await appointments.get(appointment_id)
            if current is None:
                raise ValueError(f'Appointment {appointment_id} not found')

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
            if existing:
                raise SchedulingConflict(
                    f'Resource {current["resource_id"]} already booked '
                    f'{start.isoformat()}–{end.isoformat()}')

            row = await appointments.update_slot(
                appointment_id, start, end, reason)
            await self._audit_log(conn).log_event(
                'APPOINTMENT_RESCHEDULED', self.actor_id,
                'ris_appointments', appointment_id,
                details={'from': str(current['start_time']),
                         'to': str(start), 'reason': reason})
            return dict(row)

    async def cancel(self, *, appointment_id, reason=''):
        async for conn in self._open():
            appointments, _, lifecycle, _ = self._repos(conn)
            current = await appointments.get(appointment_id)
            if current is None:
                raise ValueError(f'Appointment {appointment_id} not found')

            row = await appointments.update_status(appointment_id, 'CANCELLED')
            if current.get('order_id'):
                # SCHEDULED -> CANCELLED is the valid lifecycle transition.
                await lifecycle.transition(
                    current['order_id'], 'CANCELLED', self.actor_id, reason)
            await self._audit_log(conn).log_event(
                'APPOINTMENT_CANCELLED', self.actor_id,
                'ris_appointments', appointment_id, details={'reason': reason})
            return dict(row)

    async def available_slots(self, *, resource_id, day, slot_minutes=30,
                              day_start='08:00:00', day_end='17:00:00'):
        """Free slot windows for one resource on one day, minus booked ranges."""
        day = _as_date(day)
        start = datetime.combine(day, time.fromisoformat(day_start), tzinfo=timezone.utc)
        end = datetime.combine(day, time.fromisoformat(day_end), tzinfo=timezone.utc)

        async for conn in self._open():
            appointments, schedules, _, _ = self._repos(conn)
            windows = await schedules.for_resource(resource_id)
            existing = await appointments.for_resource(resource_id, start, end)

        window = (day_start, day_end)
        for w in windows:
            if w['day_of_week'] == day.weekday():
                window = (str(w['start_time']), str(w['end_time']))
                break

        ws = datetime.combine(day, time.fromisoformat(window[0]), tzinfo=timezone.utc)
        we = datetime.combine(day, time.fromisoformat(window[1]), tzinfo=timezone.utc)

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
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return _as_datetime(value).date()