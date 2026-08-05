# Implementation Roadmap — Front Desk / Receptionist (R08)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 6 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 registration, W2 scheduling |
| 03 | User Stories | `03-user-stories.md` | done | 7 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | 6 screens, state matrix |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 16 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: patient lookup via Files browser/patient page — no front-desk-specific FR is fully implemented | (patient lookup ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R08-01 | Patient search — patient lookup exists (Files/patient page); dedup + registration flow GATED | No registration endpoints or routes | AC-R08-01 | S |
| FR-R08-02 | Registration with HL7 ADT outbound | ADT outbound wiring (backend event) does not exist | AC-R08-02 | M |
| FR-R08-03 | Order intake | No dedicated order-intake endpoint (uses worklist create) | AC-R08-03 | M |
| FR-R08-05 | Check-in status propagation | Requires WebSocket status events to R11/R06/R07 | AC-R08-05 | M |
| FR-R08-10 | PHI minimum necessary queue view | Queue board is a new screen | AC-R08-10 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R08-04 | Appointment scheduling with conflicts | Schedule board is an R04 feature; no backend schedule API yet | AC-R08-04 | L |
| FR-R08-06 | Consent capture | No consent/forms storage endpoint | AC-R08-06 | M |
| FR-R08-07 | Insurance & authorization | Depends on R09 billing data model | AC-R08-07 | M |
| FR-R08-08 | Label/document printing | Not scoped; browser print PWA | AC-R08-08 | S |
| FR-R08-09 | Waiting queue board | New screen; depends on check-in events | AC-R08-09 | M |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; patient search FRs identified as existing.

### Phase 2: Unblock GATED requirements (next priority)
1. **HL7 ADT outbound wiring** — required for FR-R08-02 / AC-R08-02
   - Owner: Integration team; Blocks: AC-R08-02; Effort: M
   - Once done, re-run validator gate on AC-R08-02.
2. **Check-in event propagation** — required for FR-R08-05 / AC-R08-05
   - Owner: Backend; Blocks: AC-R08-05, AC-R08-09; Effort: M

### Phase 3: New screens
3. **Order intake screen** — FR-R08-03; requires order endpoint (Effort M)
4. **Queue board** — FR-R08-09; consumes check-in events (Effort M)
5. **Consent capture** — FR-R08-06; new forms storage (Effort M)
6. **Scheduling (R04 dependency)** — FR-R08-04; blocked on schedule API (Effort L)

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| HL7 ADT outbound event | FR-R08-02 | AC-R08-02 | Demographics not synced to EMR |
| WebSocket status events | FR-R08-05, FR-R08-09 | AC-R08-05, AC-R08-09 | Clinical team unaware of arrivals |
| Schedule board API (R04) | FR-R08-04 | AC-R08-04 | No online scheduling |
| Billing data model (R09) | FR-R08-07 | AC-R08-07 | Insurance data not billable |

## Next Steps (highest priority)

1. **HL7 ADT outbound event** — unblocks AC-R08-02; M effort
2. **Check-in event propagation** — unblocks AC-R08-05 and AC-R08-09; M effort
3. **Coordinate schedule API with R04** — unblocks AC-R08-04; L effort
4. Update this roadmap each sprint as FR/NFR status changes.
