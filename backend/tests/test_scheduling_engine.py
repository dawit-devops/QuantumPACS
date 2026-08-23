"""S4-10 — SchedulingEngine book() + availability (B4).

The engine is the deep module: a small public interface
(book / available_slots) hiding conflict detection, schedule-window
validation, order transition and audit. Unit tests mock the engine's
repos (test_hl7_engine pattern); the EXCLUDE backstop itself is proven
against real Postgres in test_ris_appointments.py.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from services.scheduling.engine import (
    SchedulingConflict, SchedulingEngine, SchedulingNotFound,
)


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
            engine._audit = AsyncMock()

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

    def test_book_persists_prep_instructions(self):
        # S1 (K-02): prep instructions authored at booking must be written to
        # the appointment row so the kiosk/portal read path has real text.
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
            created = {'id': 'appt-1', 'status': 'SCHEDULED'}
            engine._appointments.create = AsyncMock(return_value=created)
            engine._lifecycle = AsyncMock()
            engine._lifecycle.transition = AsyncMock(return_value={
                'id': 'ord-1', 'status': 'SCHEDULED'})
            engine._audit = AsyncMock()

            await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                prep_instructions='Fast for 4 hours before your exam',
            )

            call_kwargs = engine._appointments.create.call_args.args[0]
            assert call_kwargs.get('prep_instructions') == \
                'Fast for 4 hours before your exam'

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
        # B-4: the success path audits APPOINTMENT_BOOKED.
        engine._audit = AsyncMock()
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

    def test_book_override_reason_bypasses_prior_auth_gate(self):
        """R2-01-05: override_reason must bypass the prior-auth gate and
        audit the override so the payer team can follow up."""
        async def run():
            engine = self._engine({
                'id': 'ord-1', 'prior_auth_status': 'PENDING', 'status': 'ORDERED'})
            got = await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                override_reason='verbal approval from payer',
            )
            assert got['id'] == 'appt-1', \
                'override with reason must bypass prior-auth gate'
            engine._appointments.create.assert_awaited_once()
            # The override must be audited so the payer team can follow up.
            override_events = [
                c for c in engine._audit.log_event.call_args_list
                if 'PRIOR_AUTH_OVERRIDE' in str(c)]
            assert override_events, \
                'override must audit PRIOR_AUTH_OVERRIDE event'

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
        engine._worklist.get_by_accession = AsyncMock(return_value=None)
        engine._worklist.create = AsyncMock(return_value={'id': 'wl-1'})
        engine._worklist.update_entry = AsyncMock()
        engine._worklist.cancel = AsyncMock()
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
            with pytest.raises(SchedulingNotFound):
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
        # B-4: the success path audits APPOINTMENT_BOOKED.
        engine._audit = AsyncMock()
        return engine

    def test_orderless_book_rejects_unknown_patient(self):
        async def run():
            engine = self._engine(None)
            with pytest.raises(SchedulingNotFound) as exc:
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

class TestExclusionBackstop:
    """H2: the EXCLUDE constraint race must surface as a 409 conflict, never a 500."""

    def test_book_converts_exclusion_violation_to_conflict(self):
        async def run():
            import asyncpg
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'patient_id': 'MRN-1',
                'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            engine._appointments.create = AsyncMock(side_effect=asyncpg.exceptions.ExclusionViolationError(
                'conflicting key value violates exclusion constraint "no_double_book"'))

            from services.scheduling.engine import SchedulingConflict
            with pytest.raises(SchedulingConflict):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00',
                )

        asyncio.run(run())


class TestRescheduleCancelledSlots:
    """H4: CANCELLED appointments do not occupy capacity — reschedule into a
    slot held only by a cancelled row must succeed (mirror of book() F-03)."""

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
        engine._appointments.delete = AsyncMock()
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_reschedule_into_cancelled_held_slot_releases_and_succeeds(self):
        async def run():
            engine = self._engine({
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-2', 'resource_id': 'res-1', 'status': 'CANCELLED',
                 'start_time': '2026-08-20 10:00:00+00',
                 'end_time': '2026-08-20 10:30:00+00'},
            ])
            got = await engine.reschedule(
                appointment_id='appt-1',
                new_start_time='2026-08-20 10:00:00+00',
                new_end_time='2026-08-20 10:30:00+00')
            assert got['start_time'].endswith('10:00:00+00')
            engine._appointments.delete.assert_awaited_once_with('appt-2')

        asyncio.run(run())

    def test_reschedule_still_rejects_active_conflict_beside_cancelled(self):
        async def run():
            engine = self._engine({
                'id': 'appt-1', 'resource_id': 'res-1', 'order_id': 'ord-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00'})
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-2', 'resource_id': 'res-1', 'status': 'CANCELLED',
                 'start_time': '2026-08-20 10:00:00+00',
                 'end_time': '2026-08-20 10:30:00+00'},
                {'id': 'appt-3', 'resource_id': 'res-1', 'status': 'SCHEDULED',
                 'start_time': '2026-08-20 10:00:00+00',
                 'end_time': '2026-08-20 10:30:00+00'},
            ])
            with pytest.raises(SchedulingConflict):
                await engine.reschedule(
                    appointment_id='appt-1',
                    new_start_time='2026-08-20 10:00:00+00',
                    new_end_time='2026-08-20 10:30:00+00')
            engine._appointments.delete.assert_not_awaited()
            engine._appointments.update_slot.assert_not_awaited()

        asyncio.run(run())


class TestWorklistSync:
    """H5: worklist_entries follow the appointment lifecycle — overrides bump
    displaced orders off the MWL and re-stamp the rebooked order's entry,
    reschedules move the entry's date/time, cancels remove it."""

    def _order(self, oid, accession):
        return {'id': oid, 'accession_number': accession,
                'patient_id': 'MRN-1', 'patient_name': 'Doe, Jane',
                'patient_dob': '1980-01-01', 'referring_physician': 'Dr X',
                'clinical_indication': 'follow-up', 'priority': 'ROUTINE',
                'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'}

    def _engine(self):
        engine = SchedulingEngine(actor_id='sched-1')
        engine._appointments = AsyncMock()
        engine._appointments.create = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.for_resource = AsyncMock(return_value=[])
        engine._appointments.get = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.update_slot = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'start_time': '2026-08-20 10:00:00+00',
            'end_time': '2026-08-20 10:30:00+00', 'status': 'SCHEDULED'})
        engine._appointments.update_status = AsyncMock(return_value={
            'id': 'appt-1', 'order_id': 'ord-1', 'resource_id': 'res-1',
            'status': 'CANCELLED'})
        engine._appointments.delete = AsyncMock()
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._orders.get = AsyncMock(side_effect=lambda oid: {
            'ord-1': self._order('ord-1', 'A-1001'),
            'ord-2': self._order('ord-2', 'A-2002'),
        }[oid])
        engine._lifecycle = AsyncMock()
        engine._lifecycle.transition = AsyncMock(return_value={
            'id': 'ord-1', 'status': 'SCHEDULED'})
        engine._resources = AsyncMock()
        engine._resources.get = AsyncMock(return_value={
            'id': 'res-1', 'name': 'CT-1', 'modality': 'CT',
            'resource_type': 'MODALITY'})
        engine._worklist = AsyncMock()
        engine._worklist.get_by_accession = AsyncMock(return_value=None)
        engine._worklist.create = AsyncMock(return_value={'id': 'wl-1'})
        engine._worklist.update_entry = AsyncMock()
        engine._worklist.cancel = AsyncMock()
        engine._audit = AsyncMock()
        engine._audit.log_event = AsyncMock()
        return engine

    def test_override_cancels_bumped_orders_and_restamps_own_entry(self):
        async def run():
            engine = self._engine()
            engine._appointments.for_resource = AsyncMock(return_value=[
                {'id': 'appt-2', 'order_id': 'ord-2', 'resource_id': 'res-1',
                 'status': 'SCHEDULED',
                 'start_time': '2026-08-20 09:00:00+00',
                 'end_time': '2026-08-20 09:30:00+00'},
            ])
            engine._worklist.get_by_accession = AsyncMock(
                side_effect=lambda acc: {'id': 'wl-1'} if acc == 'A-1001'
                else {'id': 'wl-2'})
            await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                override_reason='STAT bumped')
            engine._worklist.cancel.assert_awaited_once_with('wl-2')
            args = engine._worklist.update_entry.await_args.args
            assert args[0] == 'wl-1'
            assert args[1]['scheduled_date'].isoformat() == '2026-08-20'
            assert str(args[1]['scheduled_time']) == '09:00:00'
            engine._worklist.create.assert_not_awaited()

        asyncio.run(run())

    def test_reschedule_updates_worklist_scheduled_time(self):
        async def run():
            engine = self._engine()
            engine._worklist.get_by_accession = AsyncMock(
                return_value={'id': 'wl-1'})
            await engine.reschedule(
                appointment_id='appt-1',
                new_start_time='2026-08-20 10:00:00+00',
                new_end_time='2026-08-20 10:30:00+00',
                reason='patient request')
            args = engine._worklist.update_entry.await_args.args
            assert args[0] == 'wl-1'
            assert args[1]['scheduled_date'].isoformat() == '2026-08-20'
            assert str(args[1]['scheduled_time']) == '10:00:00'

        asyncio.run(run())

    def test_cancel_removes_worklist_entry(self):
        async def run():
            engine = self._engine()
            engine._worklist.get_by_accession = AsyncMock(
                return_value={'id': 'wl-1'})
            await engine.cancel(appointment_id='appt-1', reason='cancelled')
            engine._worklist.cancel.assert_awaited_once_with('wl-1')

        asyncio.run(run())


class TestErrorContract:
    """S4 B-2/B-7/B-8 engine-level: missing entities are not-found
    outcomes, malformed datetimes are validation errors — never raw
    ValueError (which the API layer would turn into a 500)."""

    def test_book_missing_order_raises_not_found(self):
        async def run():
            from services.scheduling.engine import SchedulingNotFound

            engine = SchedulingEngine()
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value=None)
            with pytest.raises(SchedulingNotFound):
                await engine.book(
                    order_id='ord-missing', patient_id='MRN-1',
                    resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
        asyncio.run(run())

    def test_book_missing_resource_raises_not_found(self):
        async def run():
            from services.scheduling.engine import SchedulingNotFound

            engine = SchedulingEngine()
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'patient_id': 'MRN-1',
                'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            engine._resources = AsyncMock()
            engine._resources.get = AsyncMock(return_value=None)
            with pytest.raises(SchedulingNotFound):
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1',
                    resource_id='res-missing',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
        asyncio.run(run())

    def test_book_malformed_datetime_raises_validation(self):
        async def run():
            from services.scheduling.engine import SchedulingValidation

            engine = SchedulingEngine()
            with pytest.raises(SchedulingValidation):
                await engine.book(
                    order_id='', patient_id='MRN-1', resource_id='res-1',
                    start_time='garbage', end_time='2026-08-20 09:30:00+00')
        asyncio.run(run())

    def test_reschedule_missing_appointment_raises_not_found(self):
        async def run():
            from services.scheduling.engine import SchedulingNotFound

            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.get = AsyncMock(return_value=None)
            with pytest.raises(SchedulingNotFound):
                await engine.reschedule(
                    appointment_id='appt-missing',
                    new_start_time='2026-08-20 10:00:00+00',
                    new_end_time='2026-08-20 10:30:00+00')
        asyncio.run(run())

    def test_cancel_missing_appointment_raises_not_found(self):
        async def run():
            from services.scheduling.engine import SchedulingNotFound

            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.get = AsyncMock(return_value=None)
            with pytest.raises(SchedulingNotFound):
                await engine.cancel(appointment_id='appt-missing')
        asyncio.run(run())


class TestBookingAudit:
    """B-4: every successful booking must audit an APPOINTMENT_BOOKED
    event carrying resource/slot/reason — the order timeline renders it."""

    def test_book_audits_appointment_booked_with_slot_details(self):
        async def run():
            from services.scheduling.engine import SchedulingEngine

            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'patient_id': 'MRN-1',
                'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
            engine._appointments.create = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'SCHEDULED'})
            engine._lifecycle = AsyncMock()
            engine._lifecycle.transition = AsyncMock(return_value={
                'id': 'ord-1', 'status': 'SCHEDULED'})
            engine._audit = AsyncMock()
            engine._audit = AsyncMock()

            await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00', reason='routing order')

            calls = [c.args for c in engine._audit.log_event.await_args_list]
            booked = [c for c in calls if c[0] == 'APPOINTMENT_BOOKED']
            assert len(booked) == 1, f'expected 1 APPOINTMENT_BOOKED, got {len(booked)}'
            details = booked[0][4]
            assert details['resource_id'] == 'res-1'
            assert details['start_time'] == str(
                datetime.fromisoformat('2026-08-20 09:00:00+00'))
            assert details['end_time'] == str(
                datetime.fromisoformat('2026-08-20 09:30:00+00'))
            assert details['reason'] == 'routing order'
            assert details['order_id'] == 'ord-1'
        asyncio.run(run())

    def test_orderless_book_also_audits_appointment_booked(self):
        async def run():
            from services.scheduling.engine import SchedulingEngine

            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._appointments.create = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'SCHEDULED'})
            engine._audit = AsyncMock()

            await engine.book(
                order_id='', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00')

            calls = [c.args for c in engine._audit.log_event.await_args_list]
            booked = [c for c in calls if c[0] == 'APPOINTMENT_BOOKED']
            assert len(booked) == 1
            assert booked[0][4]['order_id'] is None
        asyncio.run(run())


class TestPriorAuthExpired:
    """C-7: an EXPIRED prior authorization must block booking exactly
    like PENDING/DENIED — a lapsed auth cannot hold a slot."""

    def test_book_refuses_order_with_expired_prior_auth(self):
        async def run():
            engine = SchedulingEngine()
            engine._appointments = AsyncMock()
            engine._appointments.for_resource = AsyncMock(return_value=[])
            engine._schedules = AsyncMock()
            engine._schedules.for_resource = AsyncMock(return_value=[])
            engine._orders = AsyncMock()
            engine._orders.get = AsyncMock(return_value={
                'id': 'ord-1', 'patient_id': 'MRN-1',
                'prior_auth_status': 'EXPIRED', 'status': 'ORDERED'})
            with pytest.raises(SchedulingConflict) as exc:
                await engine.book(
                    order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')
            assert 'EXPIRED' in str(exc.value)
            engine._appointments.create.assert_not_awaited()
        asyncio.run(run())


class TestStationAeStamping:
    """C1 (GAP_AUDIT_TDD_PIPELINE.md): booked MWL entries never carried the
    resource identity, so a modality filtering its C-FIND by
    ScheduledStationAE missed every RIS-booked exam (plan S6-01/02 ≥98%
    auto-fill). The resource's name is the room/AE identity — it must be
    stamped on create AND kept correct through reschedule."""

    @staticmethod
    def _engine_with_mocks(worklist_entry=None):
        engine = SchedulingEngine()
        engine._appointments = AsyncMock()
        engine._appointments.for_resource = AsyncMock(return_value=[])
        created = {
            'id': 'appt-1', 'tenant_id': 'default', 'order_id': 'ord-1',
            'resource_id': 'res-1', 'patient_id': 'MRN-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00',
            'status': 'SCHEDULED', 'reason': '',
        }
        engine._appointments.create = AsyncMock(return_value=created)
        engine._schedules = AsyncMock()
        engine._schedules.for_resource = AsyncMock(return_value=[])
        engine._orders = AsyncMock()
        engine._orders.get = AsyncMock(return_value={
            'id': 'ord-1', 'patient_id': 'MRN-1', 'accession_number': 'ACC-C1',
            'prior_auth_status': 'NOT_REQUIRED', 'status': 'ORDERED'})
        engine._lifecycle = AsyncMock()
        engine._lifecycle.transition = AsyncMock(return_value={'id': 'ord-1'})
        engine._audit = AsyncMock()
        engine._resources = AsyncMock()
        engine._resources.get = AsyncMock(return_value={
            'id': 'res-1', 'name': 'CT Room 1', 'modality': 'CT'})
        engine._worklist = AsyncMock()
        engine._worklist.get_by_accession = AsyncMock(
            return_value=worklist_entry)
        return engine

    def test_book_stamps_station_ae_from_resource(self):
        async def run():
            engine = self._engine_with_mocks()

            await engine.book(
                order_id='ord-1', patient_id='MRN-1', resource_id='res-1',
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
            )

            data = engine._worklist.create.call_args[0][0]
            assert data['station_ae_title'] == 'CT Room 1', (
                'booked MWL entry must carry the resource AE so '
                'station-scoped C-FIND finds it')
            assert data['modality'] == 'CT'

        asyncio.run(run())

    def test_reschedule_keeps_station_ae_on_moved_entry(self):
        async def run():
            engine = self._engine_with_mocks(
                worklist_entry={'id': 'entry-1', 'accession_number': 'ACC-C1'})
            engine._appointments.get = AsyncMock(return_value={
                'id': 'appt-1', 'order_id': 'ord-1',
                'resource_id': 'res-1',
                'start_time': '2026-08-20 09:00:00+00',
                'end_time': '2026-08-20 09:30:00+00',
                'status': 'SCHEDULED',
            })
            engine._appointments.update_slot = AsyncMock(return_value={
                'id': 'appt-1', 'status': 'SCHEDULED'})

            await engine.reschedule(
                appointment_id='appt-1',
                new_start_time='2026-08-21 10:00:00+00',
                new_end_time='2026-08-21 10:30:00+00', reason='conflict')

            updates = [
                c.args[1] for c in engine._worklist.update_entry.call_args_list
            ]
            assert any(u.get('station_ae_title') == 'CT Room 1'
                       for u in updates), (
                'reschedule must re-stamp station_ae_title so the entry '
                'never loses its station identity')

        asyncio.run(run())
