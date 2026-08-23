# UI/UX Redesign v2 — Portal & Kiosk TDD Implementation Plan

**Spec:** `docs/ui-ux-redesign-spec.md` (v2.0)
**Branch:** `feature/ris-integration`
**Baseline:** portal rewire committed (`6813947`); backend 2547 passed/2 skipped; FE portal suites 60 green; tsc clean.
**Method:** Vertical TDD slices — one RED test → minimal GREEN → refactor → suite gate. No horizontal batching.

## 0. Preconditions & Decisions

| ID | Decision | Resolution |
|----|----------|------------|
| D1 | New `NOTIFICATIONS_SELF` permission → `MATRIX_C_PATIENT`; gate user-scoped self notification endpoints on `[FILE_READ, NOTIFICATIONS_SELF]` | **APPROVED** |
| D2 | Kiosk payment capture via unauthenticated token-scoped path | **APPROVED** |
| D3 | Signature storage on `consent_documents` (extend) vs new columns on `ris_appointments` | **consent_documents** |

## 1. Refined Gap Backlog (post platform cross-check)

**P0**
1. Prep instructions never authored at booking (column exists, always `''`)
2. Kiosk consent/signature unpersisted (UI-only)
3. Patient cannot read notifications (`FILE_READ` gate; no `portal.*` event types)

**P1**
4. K-04 co-pay (reuse billing invoice/payment/receipt; add `invoice.order_id`)
5. K-05 queue-position/ETA from ARRIVED appointments
6. P-02 check-in badge, reminder indicator, QR link on appointments
7. P-03 history filters (modality/date/facility) + linked-report navigation
8. P-05 linked report/appointment context + time-window field in follow-up form
9. P-01 phone/email columns + profile display + front-desk capture

**P2**
10. K-02 "I understand" checkbox; K-03 decline-with-reason; kiosk UTC timezone bug
11. §3 widget registry + per-user layout persistence; §5 immersive reader

## 2. Vertical Slices (RED → GREEN → refactor → gate)

### S1 — Prep authoring (P0-1)

**Behaviors:** booking an appointment with `prep_instructions` persists it; kiosk GET returns authored text; omitted → `''`.

**RED:** scheduling tests assert INSERT carries column; schema validation accepts/rejects length.

**GREEN:** `CreateAppointmentRequest.prep_instructions` (both `ris_scheduling.py`, `frontdesk.py` schemas), pass through `SchedulingEngine.book()` + frontdesk POST; `DEFAULT_PREP` stays frontend fallback only.

**Files:** `api/schemas/ris_scheduling.py`, `api/schemas/frontdesk.py`, `services/scheduling/engine.py`, `api/frontdesk.py`, `db/ris_appointments.py`.

**Gate:** `pytest tests/test_ris_scheduling.py tests/test_ris_v21_preregistration.py -q`

### S2 — Kiosk consent persistence (P0-2)

**Behaviors:** `POST /ris/checkin/{token}/consent` stores base64 PNG signature + timestamp + refusal(reason) against the appointment's visit; token invalid → 403; repeat POST → idempotent OK.

**RED:** new `TestKioskConsent` class (token paths, storage SQL shape, audit `ris.consent_signed`).

**GREEN:** migration 089 (signature/consent columns on `consent_documents`), handler beside `PortalCheckInHandler`, route + `_PUBLIC_PATHS` allowlist entry; wire `CheckIn.tsx.handleConsentSubmit` → API call; add Decline button + reason → same endpoint `accepted=false`.

**Files:** `backend/api/checkin.py`, `backend/db/ris_appointments.py` (or `backend/db/frontdesk.py` for consent_documents), `backend/api/routes.py`, `backend/api/auth.py`, `frontend/src/kiosk/CheckIn.tsx`, `frontend/src/api/checkin.ts`, `frontend/src/test/CheckIn.test.tsx`.

**Gate:** `pytest tests/test_ris_v21_preregistration.py -q` + `npx vitest run src/test/CheckIn.test.tsx`

### S3 — Portal notifications (P0-3)

**Behaviors:** patient-role user lists own notifications + unread count; `portal.report_available` fires on report sign to scoped patient; `portal.follow_up_response` when coordinator updates follow-up; prefs endpoint honors patient gate.

**RED:** tests for `[FILE_READ, NOTIFICATIONS_SELF]` gate matrix (patient ✓, staff ✓, no-perms ✗) + event catalog entries + producers.

**GREEN:** `Permission.NOTIFICATIONS_SELF` + `MATRIX_C_PATIENT`; swap decorators on the 7 user-scoped handlers in `notifications.py` (keep admin/critical surfaces untouched); `EVENT_CATALOG` + FE `EVENT_LABELS` additions; `notify_patient_scoped` producer wiring at sign/follow-up-update.

**Files:** `backend/api/permissions.py`, `backend/api/notifications.py`, `backend/api/notify.py`, `backend/api/reports.py`, `backend/api/portal.py`, `backend/db/notification_prefs.py`, `backend/db/notifications.py`, `frontend/src/common/NotificationBell.tsx`, `frontend/src/notifications/NotificationPreferences.tsx`, `backend/tests/test_notifications.py`.

**Gate:** `pytest tests/test_notifications.py tests/test_rbac_matrix.py -q`

### S4 — Co-pay (P1-4)

**Behaviors:** token-scoped payment captures against an order-linked invoice; idempotency honored; receipt returned; skip → outstanding.

**RED:** `TestKioskPayment` — creates invoice via charge bridge, posts payment by token, asserts balance/status + audit.

**GREEN:** migration 089 adds `invoice.order_id` (+ index); create-at-order-time hook in booking/order flow; `POST /ris/checkin/{token}/payment` handler reusing `BillingPaymentsHandler` internals; allowlist entry; `CoPayPrompt.tsx` + `api/checkin.ts` client fn.

**Files:** `backend/api/checkin.py`, `backend/api/billing.py`, `backend/db/billing.py`, `backend/api/auth.py`, `backend/api/routes.py`, `frontend/src/kiosk/CoPayPrompt.tsx`, `frontend/src/api/checkin.ts`, `frontend/src/test/CheckIn.test.tsx`.

**Gate:** `pytest tests/test_ris_v21_preregistration.py tests/test_billing.py -q` + `npx vitest run src/test/CheckIn.test.tsx`

### S5 — Queue position (P1-5)

**Behaviors:** after ARRIVED, GET returns `{position, eta_minutes}` computed over same-day ARRIVED/SCHEDULED appointments for that resource; auto-refresh 60s.

**RED:** position math tests (1st/3rd/N, empty queue).

**GREEN:** `GET /ris/checkin/{token}/queue-position` (token-only); `WaitTime.tsx` polling component.

**Files:** `backend/api/checkin.py`, `backend/db/ris_appointments.py`, `backend/api/auth.py`, `backend/api/routes.py`, `frontend/src/kiosk/WaitTime.tsx`, `frontend/src/api/checkin.ts`, `frontend/src/test/CheckIn.test.tsx`.

**Gate:** `pytest tests/test_ris_v21_preregistration.py -q` + `npx vitest run src/test/CheckIn.test.tsx`

### S6 — Appointments UX (P1-6/7)

**Behaviors:** ARRIVED row shows "You're checked in ✓" badge; history tab filters by modality/date-range; completed row links to its specific report (`report_id` resolved via accession).

**RED:** FE tests (badge render, filter query params, deep-link nav); backend: appointments response gains optional `report_id` join when a final report matches the order's accession.

**GREEN:** backend join + `AppointmentList.tsx` filters/badge/link; reminder indicator from notifications presence.

**Files:** `backend/db/portal.py`, `frontend/src/portal/AppointmentList.tsx`, `frontend/src/portal/PortalHome.tsx`, `frontend/src/test/PortalHome.test.tsx`.

**Gate:** `pytest tests/test_portal_api.py -q` + `npx vitest run src/test/PortalHome.test.tsx`

### S7 — Follow-up context (P1-8)

**Behaviors:** create accepts `linked_report_id`/`linked_exam_id` prefill selector fed by patient's own reports/appointments; `preferred_time` UI select persisted (column exists).

**RED:** FE form test asserting payload; backend already validates targets — extend test for exam linkage.

**GREEN:** schema passthrough (already exists server-side), `FollowUpHub.tsx` selectors.

**Files:** `frontend/src/portal/FollowUpHub.tsx`, `frontend/src/test/PortalHome.test.tsx`.

**Gate:** `npx vitest run src/test/PortalHome.test.tsx`

### S8 — Demographics phone/email (P1-9)

**Behaviors:** registration captures phone/email; portal profile displays them; consent-status flag included in GET bundle (removes `reports.length` heuristic).

**RED:** frontdesk registration schema round-trip; portal bundle includes `phone/email/consent_results`.

**GREEN:** migration 089 `patients.phone/email`; `get_demographics` projection; registration form fields; `PatientProfile.tsx` real values; `ConsentManager.tsx` extracted per spec §2.12.5.

**Files:** `backend/db/portal.py`, `backend/api/portal.py`, `backend/api/schemas/frontdesk.py`, `backend/api/frontdesk.py`, `backend/db/patient.py`, `frontend/src/portal/PatientProfile.tsx`, `frontend/src/portal/ConsentManager.tsx`, `frontend/src/test/PortalHome.test.tsx`.

**Gate:** `pytest tests/test_portal_api.py tests/test_frontdesk.py -q` + `npx vitest run src/test/PortalHome.test.tsx`

### S9 — §3 widgets / §5 immersive (P2, deferred)

Widget registry + `PUT /users/{id}/preferences` persistence (gated `USER_WRITE`); immersive mode toggle on ReadingConsole using theme tokens.

## 3. Migration 089

Accumulates: kiosk consent storage (D3), `invoice.order_id`, `patients.phone/email`. Down-revision `088`. Alembic head bump verified by import smoke test.

## 4. Verification Gates (per slice)

1. Targeted RED fails for the stated reason
2. GREEN: slice tests pass
3. `pytest tests/test_portal_api.py tests/test_ris_v21_preregistration.py <slice-suites> -q` + affected RBAC suites
4. FE: `vitest run <touched suites>` + `npx tsc --noEmit`
5. Full backend suite before each commit

## 5. Commit Strategy

One commit per slice, messages referencing spec IDs (P-xx/K-xx) and slice numbers. Conventional commits (`feat:`, `fix:`, `chore:`). Work tree clean after each.