# Implementation Roadmap — Radiology Service Cashier (R09)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 6 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 payment, W2 reconciliation |
| 03 | User Stories | `03-user-stories.md` | done | 6 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | 6 screens |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 16 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: patient/study context via Files/patient page — no billing-specific FR is fully implemented | (patient context ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R09-09 | Read-only clinical context — patient/study context exists; no billing context in billing flow | No billing flow/endpoints | AC-R09-09 | S |
| FR-R09-10 | PHI minimum necessary in billing | Billing screens do not exist yet; must not expose clinical data | AC-R09-10 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R09-01 | Invoice & payment records | No billing endpoints | AC-R09-01 | L |
| FR-R09-02 | Payment collection | Requires payment-processor integration | AC-R09-02 | L |
| FR-R09-03 | Receipts | Depends on payments | AC-R09-03 | M |
| FR-R09-04 | Insurance claim status | External claims feed not wired; manual fallback | AC-R09-04 | M |
| FR-R09-05 | Cash reconciliation | Depends on payments | AC-R09-05 | M |
| FR-R09-06 | Refunds & adjustments | Needs approval primitive | AC-R09-06 | M |
| FR-R09-07 | Quotes & estimates | Needs procedure pricing catalog | AC-R09-07 | M |
| FR-R09-08 | Payment plans | Requires billing engine | AC-R09-08 | L |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; clinical-context scoping defined.

### Phase 2: Unblock GATED requirements (next priority)
1. **Billing data model + endpoints** — required for FR-R09-01/02/03/05
   - Owner: Backend; Blocks: AC-R09-01..03, AC-R09-05; Effort: L
   - Once done, re-run validator gate on AC-R09-01.
2. **Payment processor (tokenized)** — required for FR-R09-02
   - Owner: Backend + Security; Blocks: AC-R09-02; Effort: L

### Phase 3: Remaining screens
3. **Receipts + reconciliation** — FR-R09-03/05; M
4. **Claims status (fallback manual)** — FR-R09-04; M
5. **Refund approval workflow** — FR-R09-06; M
6. **Quotes/estimates + payment plans** — FR-R09-07/08; L

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Billing endpoints | FR-R09-01..03, 05 | AC-R09-01..03, 05 | No payments possible |
| Payment processor integration | FR-R09-02 | AC-R09-02 | No card collection |
| Claims feed | FR-R09-04 | AC-R09-04 | Manual status only |
| Approval primitive | FR-R09-06 | AC-R09-06 | Refunds unmanaged |

## Next Steps (highest priority)

1. **Billing data model + endpoints** — unblocks AC-R09-01..03/05; L effort
2. **Payment processor integration** — unblocks AC-R09-02; L effort
3. **Approval primitive** — unblocks AC-R09-06; M effort
4. Update this roadmap each sprint as FR/NFR status changes.
