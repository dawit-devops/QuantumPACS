"""S4-10 — SchedulingEngine book() + availability (B4).

The engine is the deep module: a small public interface
(book / available_slots) hiding conflict detection, schedule-window
validation, order transition and audit. Unit tests mock the engine's
repos (test_hl7_engine pattern); the EXCLUDE backstop itself is proven
against real Postgres in test_ris_appointments.py.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from services.scheduling.engine import SchedulingConflict, SchedulingEngine


class TestBook:
    def test_book_conflict_free_slot_creates_appointment_and_schedules_order(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'patient_id': 'MRN-1',
                'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            created = {
                'id': 'appt-1', 'tenant_id': 'default', 'order_id': 'ord-1',
                'resource_id': 'res-1', 'patient_id': 'MRN-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00',
                'status': 'SCHEDULED', 'reason': '',
            }
            engine._appointments.create = AsyncMock(return_value=created)
            engine._lifecycle = AsyncMock()
            engine._lifecycle.transition = AsyncMock(return_value={
                'id': 'ord-1', 'status': 'SCHEDULED'})

            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
            )

            assert got['id'] == 'appt-1'
            assert got['status'] == 'SCHEDULED'
            engine._appointments.create.assert_awaited_once()
            engine._lifecycle.transition.assert_awaited_once_with(
                'ord-1', 'SCHEDULED', engine.actor_id, '')
            engine._appointments.for_resource.assert_awaited_once()

        asyncio.run(run())

    def test_book_overlapping_slot_raises_conflict(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-9', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})

            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:15:00+00',
                    end_time='2026-08-20 09:45:00+00',
                )
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())

    def test_book_requires_schedule_window_coverage(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            # Only Monday (1) 08:00-12:00 is open; booking on that day
            # outside the window must be rejected before any insert.
            engine._schedules.for_resource = AsyncMock(return_value=[
                {'id': 'sch-1', 'day_of_week': 1,
                 'start_time': '08:00:00', 'end_time': '12:00:00'},
            ])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})

            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 13:00:00+00',
                    end_time='2026-08-20 13:30:00+00',
                )
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())


class TestBookGates:
    def _engine(self, order):
        engine = SchedulingEngine()
        engine._appointments = AsyncMock()
        engine._appointments.for_resource = AsyncMock(return_value=[])
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED',
        })
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._lifecycle = AsyncMock()
        engine._lifecycle.transition = AsyncMock(return_value={
            'id': 'ord-1', 'status': 'SCHEDULED'})
        engine._orders = AsyncMock()
        engine._orders.get = AsyncMock(return_value=order)
        # Ensure the mock order carries patient_id matching MRN-1
        if order and 'patient_id' not in order:
            order['patient_id'] = 'MRN-1'
        return engine

    def test_book_refuses_order_with_pending_prior_auth(self):
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'PENDING', 'status': 'ORDERED'})
            with pytest.raises(SchedulingConflict) as exc:
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            assert 'prior auth' in str(exc.value).lower()
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())

    def test_book_refuses_order_with_denied_prior_auth(self):
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'DENIED', 'status': 'ORDERED'})
            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())

    def test_book_proceeds_with_approved_prior_auth(self):
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'APPROVED', 'status': 'ORDERED'})
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            assert got['id'] == 'appt-1'
            engine._appointments.create.assert_awaited_once()

        asyncio.run(run())

    def test_book_refuses_when_contraindication_check_finds_reasons(self):
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            engine._contraindication_check = AsyncMock(return_value=[
                'Contrast allergy on record for MRN-1'])
            with pytest.raises(SchedulingConflict) as exc:
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            assert 'allergy' in str(exc.value)
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())

    def test_book_proceeds_when_no_contraindications(self):
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            engine._contraindication_check = AsyncMock(return_value=[])
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            assert got['id'] == 'appt-1'

        asyncio.run(run())


class TestOverride:
    def _engine(self):
        engine = SchedulingEngine(actor_id='sched-1')
        engine._appointments = AsyncMock()
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-new', 'resource_id': 'res-1', 'order_id': 'ord-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.delete = AsyncMock()
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._orders.get = AsyncMock(return_value={
            'id': 'ord-1', 'patient_id': 'MRN-1',
            'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
        engine._lifecycle = AsyncMock()
        engine._lifecycle.transition = AsyncMock(return_value={
            'id': 'ord-1', 'status': 'SCHEDULED'})
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_override_without_reason_still_conflicts(self):
        async def run():
            engine = self._engine()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-old', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'}])
            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            engine._appointments.delete.assert_not_awaited()

        asyncio.run(run())

    def test_override_with_reason_deletes_conflict_and_books(self):
        async def run():
            engine = self._engine()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-old', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'}])
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                override_reason='emergency rebook')
            assert got['id'] == 'appt-new'
            engine._appointments.delete.assert_awaited_once_with('appt-old')
            override_event = [
                c for c in engine._audit.log_event.await_args_list
                if c.args[0] == 'APPOINTMENT_OVERRIDE']
            assert override_event
            assert override_event[0].kwargs['details']['reason'] == 'emergency rebook'

        asyncio.run(run())

    def test_override_without_conflict_books_normally(self):
        async def run():
            engine = self._engine()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                override_reason='irrelevant')
            assert got['id'] == 'appt-new'
            engine._appointments.delete.assert_not_awaited()
            types = [c.args[0] for c in engine._audit.log_event.await_args_list]
            assert 'APPOINTMENT_OVERRIDE' not in types

        asyncio.run(run())


class TestWorklistLink:
    def _engine(self):
        engine = SchedulingEngine(actor_id='sched-1')
        engine._appointments = AsyncMock()
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.for_resource = AsyncMock(return_value=[])
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._orders.get = AsyncMock(return_value={
            'id': 'ord-1', 'accession_number': 'A-1001',
            'patient_id': 'MRN-1', 'patient_name': 'Doe, Jane',
            'patient_dob': '1980-01-01', 'referring_physician': 'Dr X',
            'clinical_indication': 'follow-up', 'priority': 'ROUTINE',
            'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
        engine._lifecycle = AsyncMock()
        engine._lifecycle.transition = AsyncMock(return_value={
            'id': 'ord-1', 'status': 'SCHEDULED'})
        engine._resources = AsyncMock()
        engine._resources.get = AsyncMock(return_value={
            'id': 'res-1', 'name': 'CT-1', 'modality': 'CT',
            'resource_type': 'MODALITY'})
        engine._worklist = AsyncMock()
        engine._worklist.create = AsyncMock(return_value={'id': 'wl-1'})
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_book_creates_worklist_entry_with_mapped_fields(self):
        async def run():
            engine = self._engine()
            await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            entry = engine._worklist.create.await_args.args[0]
            assert entry['patient_id'] == 'MRN-1'
            assert entry['patient_name'] == 'Doe, Jane'
            assert entry['accession_number'] == 'A-1001'
            assert str(entry['scheduled_date']) == '2026-08-20'
            assert str(entry['scheduled_time']) == '09:00:00'
            assert entry['modality'] == 'CT'
            assert entry['status'] == 'scheduled'
            assert entry['created_by'] == 'sched-1'

        asyncio.run(run())

    def test_book_worklist_failure_does_not_fail_booking(self):
        async def run():
            engine = self._engine()
            engine._worklist.create = AsyncMock(side_effect=RuntimeError('db down'))
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            assert got['id'] == 'appt-1'
            types = [c.args[0] for c in engine._audit.log_event.await_args_list]
            assert 'WORKLIST_CREATE_FAILED' in types

        asyncio.run(run())


class TestReschedule:
    def _engine(self, current_appt):
        engine = SchedulingEngine()
        engine._appointments = AsyncMock()
        engine._appointments.get = AsyncMock(return_value=current_appt)
        engine._appointments.for_resource = AsyncMock(return_value=[])
        engine._appointments.update_slot = AsyncMock(return_value={
            **current_appt,
            'start_time': '2026-08-20 10:00:00+00',
            'end_time': '2026-08-20 10:30:00+00',
        })
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_reschedule_moves_appointment_to_free_slot(self):
        async def run():
            engine = self._engine({
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            got = await engine.reschedule(
                appointment_id='appt-1',
                new_start_time='2026-08-20 10:00:00+00',
                new_end_time='2026-08-20 10:30:00+00',
                reason='patient request')
            assert got['start_time'].endswith('10:00:00+00')
            engine._audit.log_event.assert_awaited_once()

        asyncio.run(run())

    def test_reschedule_into_conflict_is_rejected(self):
        async def run():
            engine = self._engine({
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-2', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 10:00:00+00',
                 'end_time': '2026-08-20 10:30:00+00'},
            ])
            with pytest.raises(SchedulingConflict):
                await engine.reschedule(
                    appointment_id='appt-1',
                    new_start_time='2026-08-20 10:00:00+00',
                    new_end_time='2026-08-20 10:30:00+00')
            engine._appointments.update_slot.assert_not_awaited()

        asyncio.run(run())

    def test_reschedule_ignores_own_current_slot_as_conflict(self):
        async def run():
            engine = self._engine({
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-1', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            got = await engine.reschedule(
                appointment_id='appt-1',
                new_start_time='2026-08-20 10:00:00+00',
                new_end_time='2026-08-20 10:30:00+00')
            assert got['start_time'].endswith('10:00:00+00')

        asyncio.run(run())


class TestCancel:
    def test_cancel_releases_slot_and_cancels_order(self):
        async def run():
            engine = SchedulingEngine(actor_id='tech-1')
            engine._appointments = AsyncMock()
            engine._appointments.get = AsyncMock(return_value={
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            engine._appointments.update_status = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'CANCELLED'})
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._lifecycle = AsyncMock()
            engine._lifecycle.transition = AsyncMock(return_value={
                'id': 'ord-1', 'status': 'CANCELLED'})
            engine._audit = AsyncMock()
            engine._audit.log_event = AsyncMock()

            got = await engine.cancel(appointment_id='appt-1', reason='no-show')

            assert got['status'] == 'CANCELLED'
            engine._lifecycle.transition.assert_awaited_once_with(
                'ord-1', 'CANCELLED', 'tech-1', 'no-show')
            engine._audit.log_event.assert_awaited_once()

        asyncio.run(run())

    def test_cancel_missing_appointment_raises(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.get = AsyncMock(return_value=None)
            with pytest.raises(ValueError):
                await engine.cancel(appointment_id='nope', reason='x')

        asyncio.run(run())


class TestAvailableSlots:
    def test_available_slots_excludes_booked_windows(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-9',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[
                {'id': 'sch-1', 'day_of_week': 4,
                 'start_time': '08:00:00', 'end_time': '17:00:00'},
            ])

            slots = await engine.available_slots(
                resource_id='res-1', day='2026-08-20', slot_minutes=30)

            assert isinstance(slots, list)
            assert len(slots) >= 1
            booked = [s for s in slots
                      if s['start'] == '09:00' and s['end'] == '09:30']
            assert booked == []

        asyncio.run(run())

    def test_available_slots_treats_cancelled_as_free(self):
        # F-03 — a CANCELLED appointment must not occupy capacity; the slot
        # it held must reappear as free so the calendar can offer it again.
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-9', 'status': 'CANCELLED',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[
                {'id': 'sch-1', 'day_of_week': 4,
                 'start_time': '08:00:00', 'end_time': '17:00:00'},
            ])

            slots = await engine.available_slots(
                resource_id='res-1', day='2026-08-20', slot_minutes=30)

            freed = [s for s in slots
                     if s['start'] == '09:00' and s['end'] == '09:30']
            assert freed, 'cancelled slot must be offered as free'

        asyncio.run(run())


class TestOrderlessPatientCheck:
    """F-02 — order-less booking must verify the patient exists (R5-06).

    A scheduler typing a MRN directly cannot create an appointment against a
    phantom patient; the engine must reject an unknown patient_id before
    persisting.
    """

    def _engine(self, patient_row):
        engine = SchedulingEngine()
        engine._appointments = AsyncMock()
        engine._appointments.for_resource = AsyncMock(return_value=[])
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': None, 'resource_id': 'res-1',
            'patient_id': 'MRN-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._patients = AsyncMock()
        engine._patients.get_by_mrn = AsyncMock(return_value=patient_row)
        return engine

    def test_orderless_book_rejects_unknown_patient(self):
        async def run():
            engine = self._engine(None)
            with pytest.raises(ValueError) as exc:
                await engine.book(
                    order_id='', patient_id='MRN-GHOST', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            assert 'MRN-GHOST' in str(exc.value)
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())

    def test_orderless_book_accepts_known_patient(self):
        async def run():
            engine = self._engine({'id': 7, 'patient_id': 'MRN-1'})
            got = await engine.book(
                order_id='', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            assert got['id'] == 'appt-1'
            engine._patients.get_by_mrn.assert_awaited_once_with('MRN-1')

        asyncio.run(run())


class TestCancelledSlotRelease:
    """F-03 — booking over a slot held only by CANCELLED appointments must
    succeed without an override reason; cancelled rows are physically removed
    (their audit trail lives in audit_log), keeping S4-11's "slot release"
    promise real."""

    def _engine(self, existing):
        engine = SchedulingEngine(actor_id='sched-1')
        engine._appointments = AsyncMock()
        engine._appointments.for_resource = AsyncMock(return_value=existing)
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-new', 'order_id': None, 'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.delete = AsyncMock()
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_book_releases_cancelled_slot_without_override(self):
        async def run():
            engine = self._engine([
                {'id': 'appt-old', 'status': 'CANCELLED', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            got = await engine.book(
                order_id='', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')
            assert got['id'] == 'appt-new'
            engine._appointments.delete.assert_awaited_once_with('appt-old')
            events = [c.args[0] for c in engine._audit.log_event.await_args_list]
            assert 'APPOINTMENT_OVERRIDE' not in events

        asyncio.run(run())

    def test_book_still_requires_override_for_active_conflict(self):
        async def run():
            engine = self._engine([
                {'id': 'appt-act', 'status': 'SCHEDULED', 'resource_id': 'res-1',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            engine._appointments.create.assert_not_awaited()

        asyncio.run(run())