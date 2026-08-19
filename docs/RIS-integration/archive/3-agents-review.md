below is a 3-agents review of the sprint (S4) implimentation. the review is basesd on commited, tracked and untracked fies on the work tree. 
I want you to proceed inplimentation after consolidating the agents review in context of our current  TDD implimentation pipeline for full featured RIS integration in to existing code base following the dependency graph and consolidated sprint planing. so your fixes shoud aim at what we are already started implimenting(currently-S4 sprint)
task 1: consolidated 3-agent review
task 2: prioritized TDD pipline aligned implimentation plan (scoped to ris-integration-spec-sprint S5)
task 3: invoke the TDD skill and impliment

agent-1 review 
QuantumPACS Frontend Scheduling/Booking — Architecture & Correctness Review
Review scope: 12 files (schedule module, scheduling API client, shared helpers, Sidebar gating, frontdesk booking surfaces) plus cross-checked against backend/api/scheduling.py, backend/api/frontdesk.py, backend/services/scheduling/engine.py, backend/db/ris_appointments.py, backend/api/schemas/ris_scheduling.py, and frontend/src/api/client.ts.
Method: Full read of every file under review; empirical verification of the dayjs UTC slot→ISO conversion (executed with the repo's dayjs under TZ=America/Los_Angeles); route/permission cross-check in index.tsx, Sidebar.tsx, and backend handlers.
Summary: 0 Critical, 2 High, 7 Medium, 12 Low. The calendar is genuinely decomposed (modals are cleanly extracted with stable props), the seq-guard pattern is applied correctly where it exists, and the UTC slot→ISO conversion is verified correct. The main gaps: ScheduleBoard (legacy) was never retrofitted with the seq-guard/tenant-refetch conventions, the sidebar vs. route gate for /schedule-board contradict each other, modal/detail slot math is duplicated, and there are a few latent state-management hazards.
1. Component Boundaries & Separation of Concerns
High S1 — ScheduleBoard is a second, un-maintained scheduling surface that duplicates the calendar's slot machinery
- Location: frontend/src/schedule/ScheduleBoard.tsx:35-76 vs frontend/src/schedule/CalendarView.tsx:35-63 + frontend/src/schedule/boardSlots.ts
- Description: boardSlots.ts exists specifically to hold the shared slot window ("the calendar grid and the resources board both render a fixed 30-min-slot window… one module instead of being duplicated per component"), but only CalendarView imports it. ScheduleBoard re-declares BOARD_START_HOUR = 8 / BOARD_END_HOUR = 18 (boardSlots uses 7–19), SLOT_MINUTES, buildSlots() (identical implementation), and slotIndexFor() (different semantics — ScheduleBoard clamps out-of-window times to the nearest edge at lines 71-74, CalendarView returns null). Two scheduling boards now render different day windows with different index math, and the shared module's promise is half-fulfilled. The two pages also both implement the same header + prev/today/next nav block (CalendarView.tsx:211-237, ScheduleBoard.tsx:187-204).
- Fix: Parameterize and move buildSlots()/slotIndexFor()/slotSpanFor() into boardSlots.ts with an explicit window argument; have ScheduleBoard import the shared constants (it is a different, legacy window — that's fine, pass 8/18 explicitly). Extract the shared header/nav into a small ScheduleDayNav component if the two pages are to stay.
Medium S2 — CalendarView remains a ~410-line monolith owning fetch + grid + drawer + modals
- Location: frontend/src/schedule/CalendarView.tsx:72-410
- Description: The modal extraction is genuinely good — BookingFormModal, RescheduleModal, CancelModal are each single-responsibility with explicit props (open, resource/slot/appointment, onDone, onConflict), and BookingFormModal/CancelModal use stable effect deps (see S11). What remains inline in the monolith: the grid render (270-335), the per-cell busy/free derivation (149-179), the drawer (350-383), and the reschedule slot filtering (196-205, 389-396). The grid + slot-derivation is the part most likely to drift (it already differs from ScheduleBoard's).
- Fix: Extract CalendarGrid (props: resources, appointmentsByResource, freeSlotsByResource, canWrite, onCellClick, onBlockClick) and the busy/free memoization into the grid component. This makes the shared slot math (S1) a natural import.
Low S3 — dayjs.extend(utc) re-registered in 4 files
- Location: CalendarView.tsx:25, BookingFormModal.tsx:15, RescheduleModal.tsx:13, CancelModal.tsx:12
- Description: Idempotent but repeated; the UTC wall-clock convention is a cross-cutting concern of the whole schedule module.
- Fix: One frontend/src/schedule/time.ts (or fold into boardSlots.ts) that imports dayjs, extends utc, and exports slotToIso(day, "HH:MM") — which also kills the four inline dayjs.utc(\${day} ${slot.start}\`).toISOString()` copies (BookingFormModal:85-86, RescheduleModal:56-57).
2. Duplication
High D1 — Five inline MODALITIES arrays with contradictory vocabularies ("MR" vs "MRI")
- Location: ResourceManager.tsx:51; AppointmentBooking.tsx:24; ScheduleBoard.tsx:35; CreateEntry.tsx:3-15; ProtocolRegistry.tsx:27
- Description: ResourceManager and AppointmentBooking share ["CT","MR","PET","DX","US","MG","FL","XA","NM"] (identical, but copy-pasted). ScheduleBoard uses ["CT","MRI","PET","DX","MG","US","FL"] — "MRI" instead of "MR" and missing XA/NM. CreateEntry has a third set (CT, MR, XA, US, NM, PET, PT, DX, CR, MG, IO, RF…). Consequences:
- The board's modality columns union DEFAULT_MODALITIES with values seen in worklist data (ScheduleBoard:121-124), so "MRI" and "MR" render as two columns for the same physical modality — bookings created via the board's AppointmentBooking (which sends "MR") land in a separate "MR" column from DICOM-sourced "MRI" worklist entries.
- Modality is the join key for capacity (get_capacity(modality, …) in backend/api/frontdesk.py:392,460) and availability — a capacity row created for "MR" will 404 for "MRI" bookings and vice versa.
- The backend has no canonical modality list, so the frontend is the vocabulary — which makes the duplication a real data-integrity hazard, not just style.
- Fix: Single shared frontend/src/common/modalities.ts exporting the canonical array; ScheduleBoard's DEFAULT_MODALITIES should be removed or derived from the canonical list (the dynamic union with worklist data stays).
Medium D2 — Slot window constants + status colors duplicated with different values
- Location: boardSlots.ts:6-8 (7–19) vs ScheduleBoard.tsx:38-40 (8–18); CalendarView.tsx:27-33 (uppercase RIS statuses) vs ScheduleBoard.tsx:42-52 (lowercase worklist statuses, two maps)
- Description: Covered under S1 for the window. The status maps use different case conventions because the two backends (RIS ris_appointments vs legacy appointments) use different vocabularies — that part is legitimate, but the maps are still copy-paste drift risks sitting in two files.
- Fix: Keep two maps if the vocabularies truly differ, but move them next to the API types (scheduling.ts / frontdesk.ts) or a shared statusColors.ts, and derive ScheduleBoard's BOARD_STATUS_COLORS from one source.
Low D3 — toErrorMessage not adopted by the legacy booking surfaces
- Location: errors.ts:6-10 (the helper) vs ScheduleBoard.tsx:104,179, AppointmentBooking.tsx:80,144, Visits.tsx:120,163,199,219,240 (all use e.message on any casts)
- Description: All new schedule code uses toErrorMessage correctly; the three frontdesk/legacy surfaces bypass it with catch (e: any) { message.error(e.message || …) }. Works for ApiError (which always sets message), but a thrown string or unknown value renders "undefined".
- Fix: Mechanical: replace e.message || fallback with toErrorMessage(e) || fallback.
3. Timezone Handling
Medium T1 — Day label/stepping is browser-local while the backend day semantics are UTC
- Location: CalendarView.tsx:78 (dayjs().format("YYYY-MM-DD")), :234 (Today), :137-138 (changeDay)
- Description: Verified: the slot→ISO conversion is correct — running the repo's dayjs with TZ=America/Los_Angeles, dayjs.utc("2026-08-19 09:00").toISOString() returns 2026-08-19T09:00:00.000Z, and the engine (engine.py:267-268, _slot_within_windows) compares UTC wall-clock against naive schedule-window times, so bookings are UTC-consistent. The inconsistency is the day boundary: day is derived from browser-local time but interpreted by the backend as a UTC date (engine.py:252-254 combines it with timezone.utc; api/scheduling.py:109-114 queries date.fromisoformat(day) in UTC). For any user whose local date ≠ UTC date (e.g. UTC+8 between 00:00–08:00, UTC-7 after 17:00), the "Today" button and the header Tag point at a UTC day that is not the user's local today, and slot labels (UTC wall-clock) don't correspond to local wall-clock. The calendar is internally self-consistent (appointments, availability, and grid all share the UTC-day convention) — only the label/stepping anchor is wrong.
- Fix: Anchor the day in UTC: dayjs.utc().format("YYYY-MM-DD") for the initial state and the Today button, and dayjs.utc(prev).add(delta, "day") in changeDay. Optionally show a "times in UTC" hint in the header.
Low T2 — Reschedule slot filter assumes slot-boundary starts
- Location: CalendarView.tsx:196-199 and :389-396
- Description: The filter s.start !== dayjs.utc(selected.start_time).format("HH:mm") excludes the current slot by exact string equality. In practice free slots already exclude the appointment's own range (the engine subtracts busy ranges in available_slots), so this filter is redundant — but it silently does nothing for appointments starting off a slot boundary (e.g. 09:15), which would then appear as a bookable "new slot" (a no-op reschedule). Harmless today; brittle if the engine ever emits boundary-aligned slots differently.
- Fix: Drop the filter or compare against the slot range intersection rather than the start instant.
4. Stale-Response Race Protection & Tenant-Refetch
High R1 — ScheduleBoard has no seq guard (the exact race the codebase guards elsewhere)
- Location: ScheduleBoard.tsx:92-119 (fetch, fetchAppointments, useEffect)
- Description: CalendarView (CalendarView.tsx:100-128, with the comment "same pattern as Visits' detailSeq guard") and Visits' detail load (Visits.tsx:138-168) both use a monotonic fetchSeq/detailSeq ref so a slow response from an earlier day/filter never paints over a newer one. ScheduleBoard — a scheduler-facing day view where the wrong day's data is clinically misleading — has no guard: two rapid day changes, or a slow network, can land the earlier day's worklist/appointments after the newer day's, and setData/setAppointments will happily apply it. Note also fetchAppointments swallows all errors (:113 .catch(() => {})), so a failed appointments load silently shows zero booked capacity.
- Fix: Copy the CalendarView pattern verbatim: const fetchSeq = useRef(0); capture seq = ++fetchSeq.current in both fetchers; check seq === fetchSeq.current before every setData/setAppointments/setError/setLoading(false); surface the appointments error via the existing Alert instead of swallowing it.
Medium R2 — ScheduleBoard never refetches on tenant switch
- Location: ScheduleBoard.tsx:28 (imports only useDocumentTitle), :116-119
- Description: CalendarView (:135), ResourceManager (:107), and Visits (:130-133, :346) all subscribe via useTenantRefetch so a tenant switch repaints the screen. ScheduleBoard does not — after a tenant switch the board keeps showing the previous tenant's worklist entries and appointments until the user changes the day. For a front-office surface this can mean booking against the wrong tenant's capacity.
- Fix: useTenantRefetch(() => { fetch(); fetchAppointments(); });
Medium R3 — CalendarView keeps stale grid data after a fetch failure
- Location: CalendarView.tsx:121-127, 241-247
- Description: On fetch failure the code sets error but never clears appointments/freeSlots. The grid renders whenever !loading && resources.length > 0, so after navigating to a new day whose fetch fails, the header Tag shows the new date while the grid still paints the previous day's bookings under it (with an error banner). A scheduler acting on that grid acts on the wrong day's data. Visits/ScheduleBoard share the trait for their tables but there the date isn't a mutable header over the same data region.
- Fix: Clear setAppointments({})/setFreeSlots({}) at fetch start (or in the catch when seq is current), or key the rendered data by the day it was fetched for.
Low R4 — Visits list fetch has no seq guard (only the detail path does)
- Location: Visits.tsx:99-128
- Description: detailSeq protects the drawer, but the list fetch (filtered by statusFilter) is unguarded — rapid chip switching can let an earlier filter's response overwrite the newer one. Lower impact than R1 (a table), but the same class.
- Fix: Same seq-ref pattern.
Low R5 — ResourceManager schedule-drawer load has no seq guard
- Location: ResourceManager.tsx:109-119
- Description: openSchedules writes are keyed by resource id (prev[r.id]), so data can't cross resources, but schedLoading toggling is unguarded — opening A then quickly B lets A's finally flip the spinner off while B's data is still pending. Minor.
- Fix: Per-open seq or an AbortController.
5. Error Handling — 409 SLOT_CONFLICT
Low E1 — Booking/reschedule modals handle 409 correctly but leave the stale slot open for re-submission
- Location: BookingFormModal.tsx:97-106, RescheduleModal.tsx:65-74, CalendarView.tsx:189-192
- Description: The dual check (err.status === 409 || err.code === "SLOT_CONFLICT") is correct and matches the backend (api/scheduling.py:130-134,149-150 emits SLOT_CONFLICT with 409; client.ts extracts both status and code). The residual gap: after onConflict fires, the modal stays open on the same stale slot while the parent refreshes freeSlots behind it — the user can hit Confirm repeatedly and stack 409s, with no in-modal path to the refreshed slot. AppointmentBooking (frontdesk) handles this better: it shows an inline warning banner and re-fetches availability in place (AppointmentBooking.tsx:136-142).
- Fix: On conflict, either close the modal and let the user re-pick from the refreshed grid, or (like AppointmentBooking) re-fetch availability and let the modal re-sync its slot prop.
Low E2 — CancelModal has no 409 branch (correct today, but the shared modal should be conflict-aware)
- Location: CancelModal.tsx:52-53
- Description: cancelRisAppointment has no 409 path in the backend (engine.cancel never raises SchedulingConflict), so message.error(toErrorMessage(e) …) is right. Not a bug — a note that the three modals' error contracts differ (onConflict only on book/reschedule).
6. Permission Gating Consistency
Medium P1 — /schedule-board sidebar gate (WORKLIST_READ) contradicts the route gate (SCHEDULE_READ)
- Location: Sidebar.tsx:194-205 vs frontend/src/index.tsx:280-292
- Description: The sidebar item gates on WORKLIST_READ with a comment claiming the page's data comes from GET /api/worklist and that showing it to SCHEDULE_READ-only roles is a "permission dead end (R13 resident review finding P0-1)". But the route still gates on SCHEDULE_READ (index.tsx:288), and the page actually needs both: GET /api/worklist requires WORKLIST_READ (backend/api/worklist.py:21), GET /api/appointments requires SCHEDULE_READ (backend/api/frontdesk.py:426), and cancel requires SCHEDULE_WRITE. So the fix inverted the dead end: a WORKLIST_READ-only user (e.g. technologist) now sees the "Schedule" nav item and is blocked by the route gate, while a SCHEDULE_READ-only scheduler gets no nav item for a page they can open. The sidebar comment and the route comment (index.tsx:282-287, "gates on SCHEDULE_READ") describe two different gates — one of them is wrong.
- Fix: Align both gates on the page's real requirements — e.g. route permission accepting both (or the union ["SCHEDULE_READ","WORKLIST_READ"] if ClinicalRoute supports arrays), matching the sidebar's permissions array; update the stale comments.
Low P2 — Write-capable modals carry no permission gate of their own
- Location: BookingFormModal.tsx, RescheduleModal.tsx, CancelModal.tsx (exported components)
- Description: All three perform SCHEDULE_WRITE mutations without checking hasPermission — they rely on the parent (CalendarView gates every entry point at :218, :289, :371). Fine today, and the backend enforces anyway; a Low note that the exported modals are a footgun if reused on a read-only surface.
Verified consistent: CalendarView, ResourceManager, and ScheduleBoard internal write actions all gate on hasPermission("SCHEDULE_WRITE"), matching the backend's SCHEDULE_WRITE on POST/reschedule/cancel handlers (api/scheduling.py:40,70,117,139,155; frontdesk.py:443,512) — no SCHEDULE_READ/SCHEDULE_WRITE mix-ups inside the pages, and the calendar/resources sidebar gates match their routes.
7. Accessibility
Medium A1 — Free cells in the calendar grid are mouse-only; keyboard users cannot book a specific cell
- Location: CalendarView.tsx:283-294
- Description: The free-slot cells are div role="gridcell" with onClick but no tabIndex, no role="button", no onKeyDown. A keyboard-only user can open the booking modal only via the header "Book Appointment" button — which always targets the first free slot of the first resource (CalendarView.tsx:223-228) — not the cell they want. The appointment blocks (:305-318) are focusable with Enter, but free cells are not. (ScheduleBoard has the same pattern at :304-321, though there cells contain focusable blocks.)
- Fix: Give free cells tabIndex={0} + role="button" and Enter/Space handlers (or render an invisible focusable button inside the cell), with the existing aria-label retained.
Low A2 — Enter-only keyboard activation on block elements; grid role without arrow-key navigation
- Location: CalendarView.tsx:305-318, ScheduleBoard.tsx:314-319, BookingFormModal.tsx:163-170
- Description: Elements with role="button" handle Enter but not Space (the standard activation key), and the role="grid" containers (CalendarView:250-256, ScheduleBoard:282) provide no arrow-key/roving-tabindex navigation, which grid semantics imply. Order-result rows in the booking modal also lack aria-selected/aria-pressed on the selected item (visual .is-selected only).
- Fix: Add Space to the keydown handlers (or use native <button>), and add aria-selected to order results.
Low A3 — Slot grid buttons override native button semantics with role="gridcell"
- Location: AppointmentBooking.tsx:282-291
- Description: Native <button> elements are given role="gridcell", discarding button semantics in the accessibility tree (the aria-pressed and disabled are present and the slots are otherwise well-labeled, so impact is small). The calendar's AppointmentBooking a11y is otherwise the best of the reviewed files (native buttons, clear aria-labels, full/closed conveyed in labels).
- Fix: Drop the role override (keep the button) or use role="gridcell" with aria-selected on a non-button element.
8. State Management
Medium S11 — RescheduleModal reset effect depends on an unstable slots array identity
- Location: RescheduleModal.tsx:45-50 + CalendarView.tsx:389-396
- Description: The effect deps are [open, appointment?.id, slots], and the parent builds slots inline in JSX: (…).filter((s) => s.start !== …) — a new array reference on every CalendarView render. Any parent re-render while the modal is open re-runs the effect, calling setNewSlot(slots[0] ?? null) and setReason("") — wiping the user's typed reason and resetting their slot selection. Today the triggers are rare (tenant refetch, fetch completion), but it is a latent data-loss bug in the exact dep-array pattern the review targets; BookingFormModal and CancelModal get this right with primitive deps (resource?.id, slot?.start, appointment?.id).
- Fix: Memoize the prop in CalendarView (const rescheduleSlots = useMemo(…, [rescheduleFor, freeSlots])) or change the effect deps to [open, appointment?.id] and select the default slot only on open.
Low S12 — Dead code: spans computed but never used
- Location: CalendarView.tsx:280-282
- Description: const spans = blocks.some((a) => slotIndexFor(…) === si) — declared, never referenced (verified: the only occurrences are the declaration and the comment at :279). Leftover from a refactor.
- Fix: Delete the lines.
Low S13 — AppointmentBooking retains the picked patient across open/close cycles
- Location: AppointmentBooking.tsx:61-67, 152-161
- Description: pickedPatient, patientQuery, patientResults are never reset on close (only the slot/conflict are reset on open via fetchAvailability). Reopening the board-flow modal after a completed booking still shows the previous patient selected — a scheduler can accidentally confirm a booking for the wrong patient. selected is reset on open, so the slot is safe; the patient is not.
- Fix: Reset the patient-pick state in the open effect (or key the modal by open).
Low S14 — Visits pagination change uses a stale pageSize closure
- Location: Visits.tsx:410-417
- Description: onChange calls setPagination({…}) then fetch(pag.current ?? 1); fetch reads pagination.pageSize from its closure — the old pageSize (state hasn't applied). A page-size change issues the request with the previous size; the response then overwrites pagination anyway, so the visible effect is a one-request inconsistency. Same class in doCheckIn (:174 fetch(pagination.current)).
- Fix: Pass pag.pageSize explicitly into fetch (parameterize), or read it from the pag argument.
Verified-Correct Highlights
- UTC slot→ISO conversion is consistent with the engine — empirically confirmed: dayjs.utc("2026-08-19 09:00").toISOString() → 2026-08-19T09:00:00.000Z under TZ=America/Los_Angeles; the engine's _slot_within_windows compares the UTC time component against naive window times, and availability slots are built with tzinfo=timezone.utc (engine.py:253,267). All four calendar surfaces (CalendarView, BookingFormModal, RescheduleModal, CancelModal) format display times with dayjs.utc(...), matching.
- Seq guards where present are correct — CalendarView's fetchSeq (CalendarView.tsx:100-128) and Visits' detailSeq (Visits.tsx:138-168) both check seq before every state write and in finally; exactly the pattern R1 asks ScheduleBoard to adopt.
- 409 dual-check (status === 409 || code === "SLOT_CONFLICT") is consistent across booking and reschedule and matches the backend envelope parsing in client.ts:98-111.
- Write gating inside pages is uniformly SCHEDULE_WRITE and matches the backend handlers; calendar/resources sidebar gates match their routes.
- toErrorMessage is a single shared helper used consistently by all new schedule code; CancelModal's reason enforcement mirrors the backend's CancelRequest.reason min_length=1.
- Cancellation audit trail — reason-required confirm button (CancelModal.tsx:69) aligns with the backend audit event APPOINTMENT_CANCELLED (engine.py:244-246).
Priority Summary
#	Severity	Area	File:line	Issue
R1	High	Stale races	ScheduleBoard.tsx:92-119	No seq guard on the day board (codebase convention violated)
D1	High	Duplication	ScheduleBoard.tsx:35 vs ResourceManager.tsx:51 vs AppointmentBooking.tsx:24	5 modality lists; "MRI" vs "MR" breaks capacity matching/columns
S1	High	Boundaries	ScheduleBoard.tsx:35-76 vs boardSlots.ts	Shared slot module unused by the second board; windows/math drift
R2	Medium	Tenant refetch	ScheduleBoard.tsx:28,116-119	No useTenantRefetch — stale tenant data after switch
R3	Medium	Stale data	CalendarView.tsx:121-127,241-247	Fetch failure leaves previous day's grid under new date header
T1	Medium	Timezone	CalendarView.tsx:78,137-138,234	Local day anchor vs UTC day semantics (conversion itself correct)
P1	Medium	Permissions	Sidebar.tsx:204 vs index.tsx:288	schedule-board sidebar (WORKLIST_READ) vs route (SCHEDULE_READ) contradict
A1	Medium	A11y	CalendarView.tsx:283-294	Free cells mouse-only; keyboard can't book a specific cell
S11	Medium	State mgmt	RescheduleModal.tsx:45-50 + CalendarView.tsx:389-396	Unstable slots dep wipes reason/selection on parent re-render
D2	Medium	Duplication	ScheduleBoard.tsx:38-52	Inline window/status constants drift from boardSlots/CalendarView
E1	Low	409 UX	BookingFormModal.tsx:97-106	Conflict leaves stale slot open for repeat 409s
R4/R5	Low	Races	Visits.tsx:99-128; ResourceManager.tsx:109-119	List fetch / drawer load unguarded
A2/A3, D3, E2, P2, S3, S12–S14, T2	Low	Various	as listed	Keyboard Space, aria-selected, toErrorMessage adoption, modal gates, utc-extend dedup, dead spans, patient-pick retention, stale pageSize, reschedule filter
Recommended action order: (1) R1 + R2 — retrofit ScheduleBoard with the seq guard and useTenantRefetch (small, high value); (2) D1 — single modalities.ts and fix "MRI"; (3) P1 — align the schedule-board gates; (4) S11 — stabilize the RescheduleModal deps; (5) R3/T1 — day anchor and stale-grid clearing; (6) S1/D2 — consolidate slot math into boardSlots.ts; (7) A1 + the Low bucket.


Agent-2 review
QA Review: QuantumPACS Scheduling/Frontdesk Frontend Test Suite
Review Scope
Component
CalendarView.tsx
BookingFormModal.tsx
RescheduleModal.tsx
CancelModal.tsx
ResourceManager.tsx
ScheduleBoard.tsx
AppointmentBooking.tsx
Visits.tsx
api/scheduling.ts
api/frontdesk.ts
No Playwright spec exercises booking, reschedule, cancel, the S4 calendar, or the resource manager (only /schedule-board route-gate in e2e/role-based-access.spec.ts:41 and a redirect assertion in e2e/resident-workflow.spec.ts:26).
Findings by Severity
CRITICAL
CR-001 RescheduleModal.tsx has zero test coverage — the entire reschedule workflow is untested
Location: frontend/src/test/ScheduleCalendar.test.tsx:13,25 (mock declared, never asserted); frontend/src/schedule/RescheduleModal.tsx (whole file)
Description: mockReschedule is wired into the module mock but no test ever renders RescheduleModal or triggers openReschedule. The modal's slot selection (auto-select slots[0]), reason capture, rescheduleAppointment payload construction, success/onDone path, and the 409/SLOT_CONFLICT branch (RescheduleModal.tsx:65-71) are all unexercised. The CalendarView wiring (openReschedule, slot filtering to exclude the current slot, and the "No free slots available for rescheduling" guard at CalendarView.tsx:194-205) is also untested. This is a primary S4 workflow (S4-17) with a server-side conflict contract — entirely unprotected against regressions.
Recommendation: Add a full reschedule flow test in ScheduleCalendar.test.tsx:
it("reschedules an appointment to a new free slot", async () => {
  mockListAppointments.mockResolvedValue([APPT]);       // 09:00–09:30
  // freeSlots already returns 09:00, 09:30 — current slot filtered out → 09:30 only
  mockReschedule.mockResolvedValue({ ...APPT, start_time: "2026-08-20T09:30:00.000Z" });
  renderWithAuth(<CalendarView />);
  await screen.findByText("P001");

  fireEvent.click(screen.getByText("P001"));            // open drawer
  fireEvent.click(screen.getByText("Reschedule"));
  expect(await screen.findByText("Reschedule Appointment")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /09:30/ })); // pick new slot
  await userEvent.type(screen.getByPlaceholderText("Reason (optional)"), "conflict");
  await userEvent.click(screen.getByRole("button", { name: "Reschedule" }));

  await waitFor(() => {
    expect(mockReschedule).toHaveBeenCalledWith("a1", {
      new_start_time: expect.stringContaining("09:30"),
      new_end_time: expect.stringContaining("10:00"),
      reason: "conflict",
    });
  });
  expect(mockListResources).toHaveBeenCalled();         // refresh after mutation
});
Also add: (a) the "No free slots available for rescheduling" message.info path (CalendarView.tsx:200-203), and (b) a reschedule-conflict test asserting mockReschedule.mockRejectedValue({ status: 409, code: "SLOT_CONFLICT" }) triggers onConflict → refetch.
CR-002 ResourceManager.tsx has zero test coverage
Location: frontend/src/schedule/ResourceManager.tsx (whole file, 389 lines); no ResourceManager.test.tsx exists
Description: Resource creation, weekly schedule-window management, createRisSchedule payload building, the end <= start validation (ResourceManager.tsx:142-144), the duplicate-day exclusion in the day dropdown (:314-316), type/modality filters, canWrite gating of the "New Resource" button and "Schedules" button, the create drawer, and the schedules drawer are all untested. This is the sole UI for configuring the capacity that the booking engine consumes (S4-08); a regression here silently breaks availability.
Recommendation: New frontend/src/test/ResourceManager.test.tsx mirroring the ScheduleCalendar mock style:
it("creates a resource and refreshes the list", async () => {
  mockCreateRisResource.mockResolvedValue({ id: "r2", name: "MRI 1", resource_type: "MODALITY", modality: "MR", status: "ACTIVE" });
  renderWithAuth(<ResourceManager />);
  await screen.findByText("CT Room 1");

  await userEvent.click(screen.getByRole("button", { name: /new resource/i }));
  await userEvent.type(screen.getByLabelText("Name"), "MRI 1");
  await userEvent.click(screen.getByRole("button", { name: "Create Resource" }));

  await waitFor(() =>
    expect(mockCreateRisResource).toHaveBeenCalledWith(
      expect.objectContaining({ name: "MRI 1", resource_type: "MODALITY", modality: "MR" })
    )
  );
  await screen.findByText("MRI 1");
});

it("rejects a schedule window whose end is not after start", async () => {
  // open Schedules drawer, set start=17:00, end=08:00, click Add → message.error
  // and mockCreateRisSchedule NOT called
});
Also add a seedUser(["SCHEDULE_READ"]) test asserting the "New Resource" and "Schedules" buttons are absent.
CR-003 BookingFormModal 409/SLOT_CONFLICT path untested (the S4 calendar booking surface)
Location: frontend/src/schedule/BookingFormModal.tsx:97-107; frontend/src/schedule/CalendarView.tsx:189-192
Description: The frontdesk AppointmentBooking conflict is well tested (FrontDesk.test.tsx:383-416), but the calendar booking modal — the primary S4 booking surface — never exercises the conflict branch. mockBook never rejects in ScheduleCalendar.test.tsx. onConflict → handleBookingConflict → message.warning(msg) + fetch() (CalendarView.tsx:189-192) is dead code from the tests' perspective. The conflict handler is what re-syncs the grid after a double-booking race (S4-10); an untested regression here breaks the "availability may have changed" contract.
Recommendation: Add to ScheduleCalendar.test.tsx:
it("handles a 409 booking conflict by warning and refreshing", async () => {
  mockSearchOrders.mockResolvedValue({ data: [ORDER], total: 1, page: 1, per_page: 25 });
  mockBook.mockRejectedValue({ status: 409, code: "SLOT_CONFLICT", message: "Slot just taken" });

  renderWithAuth(<CalendarView />);
  await screen.findByText("CT Room 1");

  const freeCell = screen.getAllByRole("gridcell").find((c) => c.getAttribute("aria-label")?.includes("(free)"));
  fireEvent.click(freeCell!);
  await userEvent.type(screen.getByPlaceholderText("Search order (name, MRN or accession)"), "Jane{Enter}");
  await userEvent.click(await screen.findByText("Jane Roe"));
  await userEvent.click(screen.getByText("Confirm Booking"));

  await waitFor(() => expect(mockListResources).toHaveBeenCalled()); // refetch after conflict
  // and assert message.warning was invoked with "Slot just taken"
});
HIGH
HI-001 Order-less booking (direct patient ID) and order-search edge paths untested
Location: BookingFormModal.tsx:63-75 (min-2-char guard + failure toast), :77-107 (submitBooking with empty pickedOrder → order_id: ""), :79-82 (no-order/no-patient guard)
Description: The booking test only covers "search order → pick → confirm". Three distinct behaviors are unverified: (1) booking by typing a patient ID directly (no order — the modal explicitly supports it and sends order_id: ""), (2) the term.length < 2 guard that silently no-ops on short queries, (3) order search failure toast and empty-result rendering.
Recommendation:
it("books without an order by typing a patient ID directly", async () => {
  // open modal via free cell, type "P999" in "Or patient ID directly (no order)"
  await userEvent.type(screen.getByPlaceholderText("Or patient ID directly (no order)"), "P999");
  await userEvent.click(screen.getByText("Confirm Booking"));
  await waitFor(() =>
    expect(mockBook).toHaveBeenCalledWith(
      expect.objectContaining({ order_id: "", patient_id: "P999", resource_id: "r1" })
    )
  );
});

it("does not search on a single-character term and surfaces search failures", async () => {
  mockSearchOrders.mockRejectedValue({ message: "search down" });
  // type "J" + Enter → mockSearchOrders NOT called
  // type "Jane" + Enter → message.error with "search down"
});
HI-002 CalendarView day navigation and modal-state reset untested
Location: CalendarView.tsx:137-143 (changeDay), :233-235 (prev/Today/next buttons)
Description: ScheduleBoard has a next-day test, but the S4 calendar never tests Prev/Today/Next. changeDay also clears selected, bookFor, rescheduleFor, cancelFor (closing all modals/drawers on navigation) — an important interaction that can strand a user in a stale modal; unverified.
Recommendation:
it("navigates days and re-fetches appointments/availability for the new day", async () => {
  renderWithAuth(<CalendarView />);
  await screen.findByText("CT Room 1");
  const callsBefore = mockListResources.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Next day" }));
  await waitFor(() => expect(mockListResources.mock.calls.length).toBeGreaterThan(callsBefore));
  expect(screen.getByRole("grid", { name: /Schedule grid for/ }).getAttribute("aria-label"))
    .toMatch(new RegExp(dayjs().add(1, "day").format("YYYY-MM-DD")));
});

it("closes the booking modal when navigating to another day", async () => {
  // open booking modal from free cell, then click Next day
  // expect Book Appointment modal no longer present and mockBook untouched
});
HI-003 CancelModal validation guard and cancel failure path untested
Location: CancelModal.tsx:42-46 (trim + message.error("A reason is required to cancel")), :69 (okButtonProps disabled: !reason.trim()), :52-53 (cancel failure)
Description: The cancel test always types a reason. The audit-critical path — that a cancel without a reason is impossible (button disabled) and that the guard errors if invoked — is untested. Same for the cancel-failure toast.
Recommendation:
it("blocks cancelling without a reason", async () => {
  mockListAppointments.mockResolvedValue([APPT]);
  renderWithAuth(<CalendarView />);
  await screen.findByText("P001");
  fireEvent.click(screen.getByText("P001"));
  fireEvent.click(screen.getByText("Cancel"));
  const confirmBtn = screen.getByRole("button", { name: "Cancel Appointment" });
  expect(confirmBtn).toBeDisabled();          // okButtonProps disabled:!reason.trim()
  await userEvent.click(confirmBtn);          // no-op
  expect(mockCancel).not.toHaveBeenCalled();
});

it("shows an error when the cancel request fails", async () => {
  mockCancel.mockRejectedValue({ message: "Cancel failed" });
  // ... type reason, click confirm → message.error("Cancel failed"), modal stays open
});
HI-004 AppointmentBooking patient-search step (scheduler/board flow) untested; ScheduleBoard's Book button never clicked
Location: AppointmentBooking.tsx:179-222; ScheduleBoard.tsx:195-199; frontend/src/test/ScheduleBoard.test.tsx (renders with no seeded user → canBook false, button absent)
Description: All five AppointmentBooking tests pass patientId="P001", so the !patientId branch (patient search → pick → "Change") is never rendered. The board's primary booking entry (Book Appointment → AppointmentBooking with patientId="" / patientName="New patient") is never clicked. The board suite renders unauthenticated (no seedUser), so the write-gated UI is invisible to the tests.
Recommendation:
- In ScheduleBoard.test.tsx, seed SCHEDULE_WRITE + SCHEDULE_READ and add:
it("opens the booking modal from the board and books after a patient search", async () => {
  mockSearchPatients.mockResolvedValue([PATIENT]);
  mockGetAvailability.mockResolvedValue([{ time: "09:00", capacity: 2, booked: 0, state: "free" }]);
  mockCreateAppointment.mockResolvedValue({ id: "a1" });

  await userEvent.click(screen.getByRole("button", { name: /book appointment/i }));
  await userEvent.type(screen.getByPlaceholderText(/search patient/i), "Jo");
  await userEvent.click(screen.getByRole("button", { name: /select/i }));
  await userEvent.click(screen.getByRole("gridcell", { name: /09:00/ }));
  await userEvent.click(screen.getByRole("button", { name: /confirm booking/i }));

  await waitFor(() =>
    expect(mockCreateAppointment).toHaveBeenCalledWith(
      expect.objectContaining({ patient_id: "P001", scheduled_time: "09:00:00" })
    )
  );
});
- Add a test that the "Change" button clears the picked patient and returns to the search step.
HI-005 Permission gating gaps across the schedule/frontdesk surfaces
Location: CalendarView.tsx:289 (if (free && canWrite) cell guard), :218 (Book Appointment button), :371 (drawer actions); ResourceManager.tsx:189,239,301 (canWrite); Visits.tsx:300,464,529,625,696 (REGISTRATION_WRITE); ScheduleBoard.tsx:231 (canBook cancel)
Description: Only CalendarView's drawer is gated-tested (ScheduleCalendar.test.tsx:176-185). Untested gates: read-only user clicking a free grid cell must NOT open the booking modal; read-only Visits user must not see Check In / order / consent / insurance forms; ResourceManager read-only; board cancel gating.
Recommendation (extend the existing permission test in ScheduleCalendar.test.tsx):
it("does not open the booking modal when a read-only user clicks a free cell", async () => {
  seedUser(["SCHEDULE_READ"]);
  renderWithAuth(<CalendarView />);
  await screen.findByText("CT Room 1");
  const freeCell = screen.getAllByRole("gridcell").find((c) => c.getAttribute("aria-label")?.includes("(free)"));
  fireEvent.click(freeCell!);
  expect(screen.queryByText("Book Appointment")).not.toBeInTheDocument(); // modal title
  expect(mockBook).not.toHaveBeenCalled();
});
Add a Visits read-only test (seedUser(["REGISTRATION_READ"]) → no "Check In" button, no "Add Order"/"Attach Consent"/"Save Insurance" buttons in the drawer).
HI-006 Tenant refetch wiring for scheduling pages never verified
Location: CalendarView.tsx:135, ResourceManager.tsx:107, Visits.tsx:130,346 (all call useTenantRefetch)
Description: useTenantRefetch itself has unit tests, but every scheduling/frontdesk suite mocks it to () => {} (ScheduleCalendar.test.tsx:53, FrontDesk.test.tsx:86). The integration contract — that these pages actually re-fetch the new tenant's resources/appointments/visits on tenant:changed — is never asserted. ScheduleBoard doesn't use the hook at all (potential functional gap: the board won't refresh on tenant switch — worth confirming against the spec).
Recommendation: Either restore the real hook and emit tenant:changed in a test (asserting mockListResources/mockListVisits re-fire), or at minimum add an explicit test documenting the intended behavior:
it("refetches resources and appointments on tenant change", async () => {
  vi.mocked(useTenantRefetch).mockImplementation((fn: () => void) => {
    // capture the registered fetcher and invoke it after emit
    registered = fn;
  });
  renderWithAuth(<CalendarView />);
  await screen.findByText("CT Room 1");
  const before = mockListResources.mock.calls.length;
  registered();                                   // simulate tenant:changed
  await waitFor(() => expect(mockListResources.mock.calls.length).toBeGreaterThan(before));
});
MEDIUM
ME-001 Error states untested on every scheduling surface
Location: CalendarView.tsx:121-124 + :239 (fetch failure alert); ResourceManager.tsx:93-96 + :217; ScheduleBoard.tsx:102-104 + :250-263 (error + Retry — no test exists for the board's retry, unlike WaitingQueue); BookingFormModal.tsx:101-103; RescheduleModal.tsx:69-71
Description: No suite ever mockRejectedValues the list/availability fetchers. The Alert + error message paths and the board's Retry button are unverified.
Recommendation: For each surface add: mockListResources.mockRejectedValue({ message: "boom" }) → expect screen.findByText("boom"); for the board additionally assert Retry re-fires request.
ME-002 Calendar grid geometry edge cases untested (spans, busy cells, closed cells, out-of-window)
Location: CalendarView.tsx:46-63 (slotIndexFor/slotSpanFor), :149-179 (block bucketing + busy-slot exclusion), :293 ((booked)/(free)/(closed) labels)
Description: No test covers: a 60+ minute appointment spanning multiple rows (slotSpanFor > 1), a free slot inside a spanned appointment being non-clickable, an appointment starting before 08:00 or after 18:00 (skipped via slotIndexFor === null), or the (closed) aria-label for slots with no availability. Same gap for ScheduleBoard.tsx:65-76 clamping (out-of-window times clamp to edges).
Recommendation: Unit-test the pure helpers directly (they're not exported — recommend exporting slotIndexFor/slotSpanFor/buildSlots) and add a rendering test with a 60-minute appointment asserting both 09:00 and 09:30 cells read (booked) and the block renders once.
ME-003 Header "Book Appointment" shortcut button untested
Location: CalendarView.tsx:218-232 (resources[0] first free slot, disabled when no resources, "No free slot available right now" message)
Description: The primary visible CTA for schedulers (besides clicking a cell) is untested, including its disabled state when resources.length === 0 and the no-free-slot message branch.
ME-004 Over-mocking / dead mocks reduce signal quality
Location: ScheduleCalendar.test.tsx:32-48 (antd Popconfirm mock — unused: none of CalendarView/BookingFormModal/RescheduleModal/CancelModal render Popconfirm; CancelModal uses Modal.onOk), :50-55 (mocks useFetch and useVisibilityGatedInterval, neither used by CalendarView)
Description: The test mocks more than the unit under test imports. If a future refactor starts using the mocked APIs, the mock will silently mask integration issues. It also suggests copy-paste from another suite rather than intentional design. FrontDesk.test.tsx:74-81 similarly mocks ../helpers (request, isAdmin, token fns) that none of the four rendered components import.
Recommendation: Trim mocks to only what the rendered component tree imports. Keep the Popconfirm mock only where the component under test actually renders Popconfirm (ScheduleBoard).
ME-005 Visits workflow coverage is thin relative to its surface area
Location: frontend/src/test/FrontDesk.test.tsx:173-243 (Visits: 3 tests)
Description: Visits.tsx (741 lines) — consent attach, insurance save, check-in from the drawer, status-filter chips, pagination, the out-of-order detailSeq guard, and the detail-error fallback ("Visit could not be loaded.") are all untested. The checkInVisit mock (FrontDesk.test.tsx:41) bypasses the real updateVisit signature, so a broken checkInVisit API shape would not be caught here (it is caught in frontdesk-api.test.ts:38-45 — good — but the UI test asserts via the wrong seam).
Recommendation: Add consent/insurance submit tests mirroring the "adds an order" test, plus a detailSeq test (rapid-open two visits, resolve the first after the second, assert the newer detail wins).
LOW
LO-001 Leftover debug test file runs in CI
Location: frontend/src/test/dbg.test.tsx (39 lines)
Description: A "dbg" suite that shallowly renders CalendarView with a sloppy module mock (dayOfWeekLabel: (d) => String(d)) and no assertions beyond "renders". Duplicates ScheduleCalendar.test.tsx fixture setup and runs on every vitest run. Either delete it or fold its intent into the real suite.
LO-002 Minor determinism risk in the ScheduleBoard day-navigation test
Location: frontend/src/test/ScheduleBoard.test.tsx:171-172
Description: today and tomorrow are computed from two separate dayjs() calls; a midnight rollover between them (or between render and assertion) could flake. In practice negligible, but compute once: const today = dayjs(); const tomorrow = today.add(1, "day"). Otherwise the suite handles TZ/date determinism well — tests avoid asserting exact ISO timestamps and derive dates relative to real "today".
LO-003 Board "500 exam" warning and board cancel flow untested
Location: ScheduleBoard.tsx:274-281 (warning alert), :171-181 (doCancelAppointment), :231-244 (cancel Popconfirm)
Description: The truncation warning for a 500-exam day and the board's cancel-appointment flow (which re-fetches both worklist and appointments) are untested. Board tests run unauthenticated so canBook is false.
Positive Findings (what's working well)
- Contract-pinning API tests: scheduling-api.test.ts and frontdesk-api.test.ts pin every request path/method/unwrap shape, which is exactly what makes the aggressive module-level mocks in the component suites safe. This is the right layering.
- Mock accuracy: checkInVisit: (id) => mockUpdateVisit(id, { status: "checked_in" }) (FrontDesk.test.tsx:41) mirrors the real delegation; helpers.request re-export mock (ScheduleBoard.test.tsx:16-23) matches helpers.ts:3.
- Behavior-first assertions: Tests query roles/aria-labels/text (getByRole("gridcell"), aria-label with (free)/(booked), getByPlaceholderText) rather than CSS classes — robust to restyling.
- Conflict-path rigor in the frontdesk modal: The 409 test (FrontDesk.test.tsx:383-416) asserts the message surfaces, availability reloads, the modal stays open, and no false onBooked fires — the correct assertion set for a double-booking race.
- Determinism discipline: Booking/reschedule payload assertions use objectContaining and avoid exact timestamps; fixtures use UTC instants that map to fixed grid slots.
- WaitingQueue HIPAA test (FrontDesk.test.tsx:264-271) deliberately seeds a leaked full name and asserts it is never rendered — a model security-behavior test.
- Strong test infra: setup.ts fails loudly on unmocked fetch, patches matchMedia/ResizeObserver/getComputedStyle honestly, and prevents localStorage leakage between tests.
Prioritized Action Plan
1. P0 — Write ResourceManager.test.tsx (CR-002) and the reschedule flow tests (CR-001); both are entire untested workflows.
2. P0 — Add the BookingFormModal 409 conflict test (CR-003) — the core S4 conflict contract.
3. P1 — Add day-navigation, order-less booking, cancel-validation, and patient-search-step tests (HI-001..HI-004).
4. P1 — Extend permission-gating tests to cell-click, Visits read-only, and ResourceManager read-only (HI-005); restore/verify tenant-refetch wiring on scheduling pages (HI-006).
5. P2 — Cover error/Retry states and grid-geometry edge cases (ME-001..ME-003); trim dead mocks (ME-004); expand Visits workflow tests (ME-005).
6. P3 — Delete dbg.test.tsx (LO-001), fix the two-dayjs() call (LO-002), add board cancel/500-warning tests (LO-003), and consider a Playwright spec for the booking→reschedule→cancel happy path.
Methodology Note
All claims above were verified by reading the actual files: ScheduleCalendar.test.tsx, scheduling-api.test.ts, ScheduleBoard.test.tsx, FrontDesk.test.tsx, frontdesk-api.test.ts, useTenantRefetch.test.tsx, route-gates.test.tsx, dbg.test.tsx, setup.ts, renderWithApp.tsx, and the components CalendarView, BookingFormModal, RescheduleModal, CancelModal, ResourceManager, ScheduleBoard, AppointmentBooking, Visits, plus api/scheduling.ts, api/frontdesk.ts, helpers.ts, AuthContext.tsx, and index.tsx route gates. The coverage/ directory predates the S4 scheduling components (only ScheduleBoard appears), so it cannot be used as evidence of current coverage — the gaps above are established directly from the test sources.


agent-3 review

Security Audit: QuantumPACS Scheduling / Booking / RIS Frontdesk
Date: 2026-08-19
Mode: Read-only review (no files modified)
Files reviewed (13 primary): CalendarView.tsx, BookingFormModal.tsx, RescheduleModal.tsx, CancelModal.tsx, ResourceManager.tsx, ScheduleBoard.tsx, AppointmentBooking.tsx, Visits.tsx, api/scheduling.ts, api/client.ts, common/errors.ts, auth/AuthContext.tsx
Cross-checked: backend/api/scheduling.py, frontdesk.py, ris_orders.py, services/scheduling/engine.py, api/permissions.py, api/rbac.py, api/tenant_middleware.py, api/auth.py, api/routes.py, api/validate.py, api/schemas/*, db/ris_appointments.py, db/ris_resources.py, db/ris_orders.py, db/frontdesk.py, db/worklist.py, api/worklist.py, frontend/src/index.tsx, common/Sidebar.tsx, auth/PermissionRoute.tsx, api/session.ts, helpers.ts, config.ts, navigator.ts
Executive Summary
The scheduling/frontdesk implementation is generally well-defended: no XSS sinks exist anywhere in the frontend (no dangerouslySetInnerHTML/innerHTML/eval in the entire src/ tree — verified by grep), all DB access is parameterized (asyncpg $1 binds / pypika bound parameters — no SQL injection), auth cookies are HttpOnly + SameSite=Strict with a central Set-Cookie hardening middleware, tokens never appear in query strings or JS-accessible storage, and route-level + button-level permission gating is consistent with backend decorators for every flow reviewed.
The findings cluster in three backend areas the frontend relies on: (1) the RIS booking engine's order-less path skips the patient-existence check that the frontdesk path enforces (its own documented R5-06 policy), allowing phantom/mismatched-patient appointments; (2) cancelled RIS appointments permanently occupy capacity (availability sabotage / stuck slots); (3) the worklist endpoint has an unclamped per_page enabling bulk PHI dumps. Plus several Low-severity hygiene items (static CSRF token, localStorage identity mirror, unhandled 500s on malformed input, unbounded string fields).
Findings: 11 total — 0 Critical, 0 High, 3 Medium, 8 Low/Info.
Findings Summary
#	Severity	CVSS	CWE
F-01	Medium	5.3	CWE-770 / CWE-200
F-02	Medium	4.3	CWE-345
F-03	Medium	5.3	CWE-770
F-04	Low	2.6	CWE-352
F-05	Low	3.1	CWE-525
F-06	Low	3.7	CWE-248
F-07	Low	2.6	CWE-770
F-08	Low	2.6	CWE-20
F-09	Low	3.1	CWE-280
F-10	Info	—	CWE-285
F-11	Info	—	CWE-400
Detailed Findings
F-01 — Medium Unbounded per_page on worklist allows bulk PHI dump (CVSS 5.3, CWE-770/CWE-200)
Location: backend/api/worklist.py:28-29 → db/worklist.py:187 (via frontend/src/schedule/ScheduleBoard.tsx:95-97)
# backend/api/worklist.py
page = int(request.query_params.get('page', '1'))
per_page = int(request.query_params.get('per_page', '20'))   # ← never clamped
...
entries, total = await Worklist(conn).search(..., page=page, per_page=per_page)
Unlike every sibling endpoint (ris_orders.py:69 clamps to 100, frontdesk.py:250 clamps to 200, users.py:282 clamps to 200), WorklistHandler.get passes per_page straight through. db/worklist.py:187 binds it into LIMIT (parameterized — no injection), but a legitimate user with WORKLIST_READ (physician, receptionist, technologist, care_coordinator, tenant_admin — see permissions.py matrices) can request per_page=2147483647 and dump the entire worklist for the tenant — full patient names, MRNs, DOBs, accessions, requesting physicians — in one response, and force the DB to materialize the whole table (memory DoS).
Attack scenario: GET /api/worklist?per_page=999999999&date_from=1970-01-01 with a valid session cookie. Any clinical staff role can exfiltrate the tenant's complete PHI schedule in a single call, or hammer it to degrade the DB.
Remediation: clamp like siblings:
try:
    page = max(1, int(request.query_params.get('page', '1')))
    per_page = min(200, max(1, int(request.query_params.get('per_page', '20'))))
except (TypeError, ValueError):
    return validation_error('Invalid pagination parameters')
(Frontend ScheduleBoard.tsx:96 also requests per_page: "500" — reduce to ≤200 to match.)
F-02 — Medium Booking engine skips the patient-existence check; order/patient mismatch allowed (CVSS 4.3, CWE-345)
Location: backend/services/scheduling/engine.py:88-149; backend/api/scheduling.py:117-135; frontend surface BookingFormModal.tsx:77-107
The frontdesk booking path enforces R5-06 ("Never schedule against a phantom patient") at frontdesk.py:471-476:
patient = await fd.get_patient(body.patient_id)
if not patient:
    return not_found('Patient not found')   # neither appointment nor worklist entry created
The RIS calendar path (RisAppointmentsHandler.post → SchedulingEngine.book) has no patient lookup at all. For order-less bookings (scheduler types any patient ID, BookingFormModal.tsx:90), book() stores body.patient_id verbatim (engine.py:137). Additionally, when an order_id is supplied, the engine never verifies order['patient_id'] == body.patient_id — the appointment is created with the caller-supplied patient while the worklist hand-off uses order['patient_id'] (engine.py:173-174), producing appointments attributed to one patient while the linked order belongs to another.
Attack scenario: A SCHEDULE_WRITE holder (receptionist/scheduler) POSTs {"order_id": "<order-of-patient-A>", "patient_id": "P<patient-B>", ...} to /api/ris/appointments. The appointment records patient B, the order transitions to SCHEDULED, and the modality worklist entry carries patient A — a wrong-patient scheduling event with downstream imaging/reading consequences (misattributed study). Or book against a nonexistent MRN to pollute the worklist/queue.
Remediation (in engine.py:book):
if order is None and patient_id:
    # Mirror R5-06: refuse phantom-patient bookings.
    from db.frontdesk import FrontDesk
    patient = await FrontDesk(conn).get_patient(patient_id) if conn else None
    if patient is None:
        raise SchedulingConflict(f'Patient {patient_id} not found')
elif order is not None:
    if order.get('patient_id') != patient_id:
        raise SchedulingConflict(
            'order.patient_id and booking patient_id must match')
F-03 — Medium CANCELLED appointments permanently occupy capacity (CVSS 5.3, CWE-770)
Location: engine.py:116-122 (book), engine.py:258-259 (available_slots), db/ris_appointments.py:37-41 (EXCLUDE constraint), surfaced via CalendarView.tsx:167-179 (free-slot map)
RisAppointments.for_resource (ris_appointments.py:65-72) applies no status filter, and the no_double_book EXCLUDE constraint (ris_appointments.py:37-41) also ignores status. Consequences:
1. available_slots() counts CANCELLED rows as busy — after CancelModal.tsx cancels an appointment, CalendarView's slot map (slotByResourceSlot, CalendarView.tsx:167-179) never shows that slot free again, so it cannot be rebooked through the UI.
2. book() raises SchedulingConflict for any overlap with a CANCELLED row unless override_reason is supplied — but the UI never sends override_reason (BookAppointmentInput, scheduling.ts:132-146).
3. The override path (engine.py:127-128) physically DELETEs conflicting rows — including CANCELLED ones, which is the only way to free a slot.
Attack scenario: a disgruntled SCHEDULE_WRITE holder cancels every appointment in a resource's prime window; the slots become permanently unbookable (stealth availability DoS, audit-logged only as legitimate cancels). Even without malice, every routine cancel permanently burns capacity until an admin manually deletes rows.
Remediation: exclude cancelled rows from both queries, and drop cancelled appointments from the EXCLUDE range (partial/exclude or status <> 'CANCELLED'):
# ris_appointments.py for_resource / engine queries
& (self.table.status != 'CANCELLED')
plus a data migration to DELETE FROM ris_appointments WHERE status = 'CANCELLED' and/or an exclusion on the constraint (EXCLUDE ... WHERE (status IS DISTINCT FROM 'CANCELLED')).
F-04 — Low Static X-CSRF-Token: "1" is a token in name only (CVSS 2.6, CWE-352)
Location: frontend/src/api/client.ts:144-147, frontend/src/api/session.ts:86
options.headers = new Headers({
  "Content-Type": "application/json",
  "X-CSRF-Token": "1",   // constant — not a real anti-CSRF token
});
Every request (including the refresh call) sends the literal value "1". The backend does not appear to verify this header at all. Actual CSRF protection comes entirely from SameSite=Strict on the auth cookies (users.py:176-194, oauth.py:461-468, plus the central hardening in app.py:152-154), which is effective in modern browsers. If SameSite is ever relaxed (e.g., for an OAuth/embedded flow) or a legacy browser is in use, there is zero defense against cross-site POST/DELETE on booking, cancel, reschedule, and check-in endpoints.
Remediation: either drop the header (it's theater), or implement a real double-submit token — e.g. server sets a csrf_token cookie on login and the client echoes it:
const csrf = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)?.[1] ?? "1";
options.headers = new Headers({ "Content-Type": "application/json", "X-CSRF-Token": csrf });
F-05 — Low Identity/permission mirror in localStorage is client-tamperable (CVSS 3.1, CWE-525)
Location: frontend/src/auth/AuthContext.tsx:49-67 (hydration) and 105-115 (write on sign-in); consumed by hasPermission at 91-96, helpers.ts:68-70 (isAdmin)
userId, username, admin, role, permissions, tenant_id, tenant_name are persisted to localStorage, and hasPermission()/route guards evaluate from that mirror. Tokens themselves are correctly HttpOnly cookies (session.ts:3-15 — no token material in JS storage), so server-side privilege escalation is not possible — every API call is re-authorization-checked (rbac.py:29-51) and tenant-scoped (tenant_middleware.py:42-87, auth.py:28-50). However:
- A user can edit localStorage.admin="true" / inject permissions to reveal admin UI, bypass frontend guards, and learn the API surface — each call then 403s, but it breaks the "security in depth" layer.
- localStorage is readable by any XSS or browser extension; username/role/tenant_id are identity metadata that would be instantly harvested (no PHI, but account-reconnaissance value).
- Role/permission changes by an administrator do not propagate until full re-login.
Remediation: keep the authoritative profile in memory only (initialized from the login//account/profile response), persist only a non-authoritative tenant_id needed by the API layer for the X-Tenant-ID header (per-request server enforcement already exists). At minimum, stop trusting admin/permissions from storage in hasPermission() and derive the initial state from the profile endpoint.
F-06 — Low Unhandled exceptions → 500s on malformed input (CVSS 3.7, CWE-248)
Locations:
- backend/api/scheduling.py:109-110 — date.fromisoformat(day) (ValueError → 500) and params['resource_id'] (KeyError → 500)
- backend/api/scheduling.py:92-98 — SchedulingEngine().available_slots(...) → engine.py:252 _as_date(day) → datetime.fromisoformat (ValueError → 500)
- engine.py:95,206,237 — ValueError for missing order/appointment, not caught by scheduling.py handlers (only SchedulingConflict is) → 500 instead of 404/409
- backend/api/worklist.py:28-29 — int() on non-numeric → 500 (siblings catch with validation_error, e.g. frontdesk.py:244-248)
Impact: error-log noise, existence oracles for arbitrary appointment/order UUIDs (500 vs 404 distinguishes existing-but-wrong-state from nonexistent), and a cheap authenticated DoS on the request handler (though no crash). The frontend handleResponse (client.ts:80-112) handles these gracefully, so user impact is limited.
Remediation: wrap date parsing and validate required params like frontdesk.py:244-248 does; catch ValueError in the handlers and return 404/422; or route ValueError through an exception middleware mapping to 404.
F-07 — Low Unbounded string fields in request schemas (CVSS 2.6, CWE-770)
Locations: backend/api/schemas/ris_scheduling.py:38-45 (CreateAppointmentRequest.patient_id, reason, override_reason — no max_length); backend/api/schemas/frontdesk.py (policy_number, guarantor_name, notes, indication, file_name, consent_type, referring_physician — all unbounded)
The 1MB body cap (validate.py:13) bounds each request, but single fields can carry ~1MB of text that is stored in TEXT columns and later rendered into the frontdesk/calendar UI (React-escaped, so no XSS, but storage bloat and unwieldy UI payloads). The frontend provides no maxLength on most of these inputs either (Visits.tsx:540-568,702-720, BookingFormModal.tsx:191-196).
Remediation: add max_length constraints mirroring the DB column semantics:
class CreateAppointmentRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=64)
    reason: str = Field('', max_length=500)
    override_reason: str = Field('', max_length=500)
F-08 — Low Whitespace-only override_reason bypasses the mandatory-reason intent (CVSS 2.6, CWE-20)
Location: backend/services/scheduling/engine.py:119-132
if not override_reason:          # '   ' is truthy → bypasses
    raise SchedulingConflict(...)
overrode = [str(a['id']) for a in existing]
for appt in existing:
    await appointments.delete(appt['id'])   # destructive override without a real reason
A SCHEDULE_WRITE holder can delete any overlapping appointment (including another patient's) and supply "   " as the audit reason — the audit row (engine.py:129-132) records a meaningless reason, defeating the override audit trail. The frontend never sends override_reason (good), but the API surface permits it.
Remediation:
if not override_reason.strip():
    raise SchedulingConflict('override_reason is required to override an existing booking')
F-09 — Low Check-in endpoint permission inconsistent with the flow that uses it (CVSS 3.1, CWE-280)
Location: backend/api/frontdesk.py:206-233 (RisPatientCheckInHandler gated on Permission.SCHEDULE_WRITE) vs frontend/src/frontdesk/Visits.tsx:135-136 → PUT /visits/{id} (VisitHandler.put gated on REGISTRATION_WRITE, frontdesk.py:298-334)
The Visits UI performs check-in via updateVisit() (REGISTRATION_WRITE), never via the SCHEDULE_WRITE-gated /ris/patients/{id}/check-in endpoint. The grants happen to coincide for receptionists, but the divergence is a latent confusion risk: if a future role receives SCHEDULE_WRITE without REGISTRATION_WRITE (e.g. a scheduler role), they'd get a check-in capability the UI model doesn't anticipate, and vice versa. Unify on the lifecycle owner (REGISTRATION_WRITE) or align both gates with the canonical visit-lifecycle permission.
F-10 — Info ScheduleBoard route gate ≠ data endpoint gate
Location: frontend/src/index.tsx:280-291 (route gate SCHEDULE_READ) vs backend/api/worklist.py:21 (WORKLIST_READ) and Sidebar.tsx:199-205 (sidebar gate WORKLIST_READ)
The board's day data comes from GET /api/worklist (ScheduleBoard.tsx:95-97) gated WORKLIST_READ, but the route gate is SCHEDULE_READ. Per the permission matrices, physician/resident/care_coordinator hold WORKLIST_READ but not SCHEDULE_READ (permissions.py:251-293) — they get a sidebar entry and an API grant, but the route redirects them (dead-end, comment acknowledged in index.tsx:282-287). No privilege escalation (the reverse direction would be the risk and no role holds SCHEDULE_READ without WORKLIST_READ), purely a UX/permission-model drift. Align the route gate with WORKLIST_READ or add SCHEDULE_READ to the physician set.
F-11 — Info Calendar fetch fan-out and no rate limiting on booking endpoints
Location: CalendarView.tsx:107-110 (2×N parallel requests per day), backend/api/scheduling.py (no rate limiting on book/reschedule/cancel, unlike login/refresh/api-keys)
With N resources the calendar fires 2N requests on every day change; a resource-heavy tenant combined with rapid day-cycling is self-inflicted load. Booking endpoints are mutation-heavy (with override able to delete rows) and have no throttling beyond auth — an authenticated SCHEDULE_WRITE holder can script mass bookings/cancellations (capacity exhaustion; audit-logged, but noisy). Consider a per-user token bucket on booking mutations (mirroring RedisTokenBucket in auth.py:95) and a Promise.all concurrency cap in CalendarView.
Verified-Healthy Areas (what is done right)
1. No XSS sinks — zero dangerouslySetInnerHTML/innerHTML/document.write/eval in the entire frontend/src tree. All DICOM/HL7/patient data (patient names, MRNs, referring physicians, procedure descriptions, notes, file names, policy numbers) renders in JSX text nodes or AntD text surfaces, which React escapes. sanitizeMessage (client.ts:45-56) additionally strips control characters and caps error strings at 240 chars before they reach message.error()/Alert.
2. No SQL/path injection — all queries parameterized (asyncpg $N binds; pypika bound parameters) including the wildcard ILIKE search paths (ris_orders.py:100-106, frontdesk.py:22-33, worklist.py:165-180). FrontDesk.update_patient (frontdesk.py:74-82) interpolates only schema-derived column names; values are bound.
3. Token hygiene — JWT access + refresh tokens live only in HttpOnly cookies (session.ts:3-15, auth.py:277); JS-readable storage holds no token material; query-string token is share-key-only and restricted to read-only file endpoints (auth.py:279-301,368-386); no hardcoded secrets in config.ts or the reviewed files.
4. CSRF mitigation — all cookies set with SameSite=Strict + HttpOnly (users.py, oauth.py), enforced centrally for any Set-Cookie (app.py:152-154); all state changes ride POST/PUT/DELETE.
5. Tenant isolation — X-Tenant-ID from localStorage (client.ts:155-158) is server-gated through can_access_tenant/can_mutate_tenant with JWT-claim priority and per-tenant DB pools (tenant_middleware.py:40-87, auth.py:28-69); header tampering cannot escape the user's grant scope.
6. Permission gating consistency — route guards (ClinicalRoute/PermissionRoute), sidebar items, and button-level hasPermission checks match backend decorators for book/reschedule/cancel/create-resource/schedule-window/check-in/order intake across all reviewed pages; backend enforces on every request (rbac.py:54-66).
7. Conflict-safe booking — capacity double-booking prevented at the DB level (advisory xact lock + capacity recheck in frontdesk.py:446-470; EXCLUDE constraint in ris_appointments.py:37-41) with 409 SLOT_CONFLICT surfaced correctly to all three booking UIs.
8. Retry safety — fetchWithRetry retries GETs only (client.ts:121-122), preventing duplicate mutations; single-flight token refresh with rate-limit awareness (session.ts:56-104).
9. Input validation — backend Pydantic v2 + 1MB body cap + clamps on page sizes (except F-01) + visit lifecycle state machine (frontdesk.py:52-57,309-322).
Recommended Remediation Priority
1. P1 (next sprint): F-01 (clamp per_page), F-02 (patient-existence + order/patient match in engine.book), F-03 (exclude CANCELLED from capacity).
2. P2 (current sprint): F-04 (real CSRF token or drop the static header), F-06 (validate/clamp date + catch ValueError in scheduling handlers), F-07 (schema max_lengths), F-08 (strip before override check).
3. P3 (backlog): F-05 (move identity profile to memory), F-09 (unify check-in permission), F-10 (align board route gate), F-11 (rate-limit bookings, cap calendar fan-out).


