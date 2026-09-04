# UI/UX Redesign TDD Plan — §2.6 Billing/Coder & §2.7 Care Coordinator

Round 4 of the per-role implementation review of `docs/ui-ux-redesign-spec.md`
(follows Front Desk §2.1, Technologist §2.3, Radiologist/Resident §2.4-2.5
rounds on `feature/ris-integration`).

## Audit method

Three parallel read-only audits (frontend / backend / platform-inheritance),
gaps refined through the platform-inheritance rule. Special attention this
round: duplication risks between the v2 cashier stack (`/api/billing/*`,
migration 037) and the RIS charge-capture stack (`/api/ris/billing/*`,
migrations 077-081).

## Verdict summary

### §2.6 Billing (~65% INHERIT)

| # | Feature | Verdict |
|---|---------|---------|
| B-01 | Billing queue | INHERIT-FULL (`RisBillingQueueHandler` billing.py:810; 30s poll BillingQueue.tsx:21; drop w/ code override billing.py:828-885) |
| B-02 | 837 claim submission | PARTIAL → **BS3**: claim stub + lifecycle exist (DRAFT…DENIED, migrations 077/081); missing claims-list endpoint, review UI, batch submit. True X12 837 serialization remains out of scope (documented stub) |
| B-03 | Patient responsibility | GAP → **BS4**: eligibility already carries copay/deductible (`frontdesk.py:741`); compose responsibility endpoint |
| B-04 | Payment posting 835 | DEFER (P2; must reuse v2 payment ledger — flagged triplication risk) |
| B-05 | Batch charge drop | GAP → **BS2**: batch = loop over proven `drop_charge` primitive + Worklist batch-bar pattern |
| B-06 | Claim status tracking | PARTIAL → **BS3**: only DENIED/RESUBMITTED listable today; need all-claims list + payer/date/status filters + drill-in (history endpoint exists billing.py:1060) |
| B-07 | Revenue dashboard | GAP → **BS5**: fragments exist (unbilled count, denial rate in ris_dashboard.py; aging buckets billing.py:917); follow ReadingStats days-clamped pattern |
| B-08 | Payer contract rates | DEFER (P2 greenfield) |
| B-09 | Fee schedule | DEFER (P2; catalog upsert exists, versions/payer overrides later) |
| B-10 | Denial rework | INHERIT-FULL core → batch-rework folded into **BS2** pattern family |
| B-11 | Unbilled aging | INHERIT-FULL → CSV export added in **BS6** |
| B-12 | CPT/ICD-10 suggestions | PARTIAL → **BS1**: BUG — queue passes accession_number as `procedure` key (BillingQueue.tsx:67 vs api signature); add confidence score + modality input |

### §2.7 Care Coordinator (~55% INHERIT)

| # | Feature | Verdict |
|---|---------|---------|
| CC-01 | Orders lifecycle view | INHERIT-FULL (Orders.tsx:48-83 derived status + >24h/>72h age tags + stuck summary) — but ZERO tests → **CS8** test debt |
| CC-02 | Care plans | GAP → **CS5** (CARE_PLAN_WRITE pre-granted to coordinator, gates nothing yet) |
| CC-03 | Encounters | GAP → **CS6** (ENCOUNTER_WRITE likewise dead-but-granted) |
| CC-04 | Communication log | GAP (outbound ris_message_log telemetry only) → **CS7** |
| CC-05..CC-08 | Referrals / discharge / meds / handoff | DEFER (all P2; CC-07 needs external FHIR EMR adapter) |
| CC-09 | Read-only patient chart | PARTIAL → **CS3** tabs composed from EXISTING endpoints (no third aggregate — flagged shadow risk) |
| CC-10 | Report summary on patient page | INHERIT → recommendations excerpt added to `/reports/priors` payload in **CS3** |
| CC-11 | Prior auth management | PARTIAL → **CS1**. TWO defects: (a) REQUIRED→PENDING transition unreachable — `submit_for_review()` has zero callers so API-created requests can never be decided; (b) **PRIOR_AUTH_WRITE held by NO staff role** → grant request below. Plus missing override-with-reason verb; expiring-soon client fn unused |
| CC-12 | Appointment reminders | PARTIAL → **CS4**: per-patient opt-out registry (today tenant-level gate only); send/config also blocked by the PRIOR_AUTH_WRITE gap |
| CC-13 | Patient quick search | INHERIT → **CS2**: overlay currently mounted on /frontdesk routes only; extend mount |

### Cross-cutting

- Widget catalogs (16 ids): no configurable widget system exists for any role
  → unchanged platform-ADR deferral from round 3.
- Duplication risks recorded: two claim models (v2 `claim` vs `ris_claims`
  — RIS canonical for these flows), two "reconciliation" nouns, three-way
  money-ledger risk for B-04, three-patient-detail risk for CC-09.

## Permission review (directive #4) — ONE grant request

Current holdings:
- `cashier` = `MATRIX_A_BILL` (permissions.py:247-250,388): BILLING_READ,
  BILLING_WRITE, PATIENT_READ, ORDER_READ, REPORT_READ, CHART_READ,
  RESULTS_READ → every shipped `/api/ris/billing/*` gate passes; no RBAC gap.
- `care_coordinator` = `MATRIX_B_COORD` (permissions.py:294-306,437): ORDER_*,
  PRIOR_AUTH_READ (not WRITE), CARE_PLAN_WRITE, ENCOUNTER_WRITE (both dead),
  PATIENT_READ, REPORT_READ, etc.

**Grant request G2 (for human review): add `PRIOR_AUTH_WRITE` to
`MATRIX_B_COORD`.**

Justification: PRIOR_AUTH_WRITE is held by NO staff built-in role (only
super_admin). It gates CC-11 create (`prior_auth.py:45`) and approve/deny
(:73) — both P0 spec rows — plus CC-12 reminder send/config
(`reminders.py:26,:78`). Care coordinators are the spec'd owners of both
workflows; without the grant the P0 prior-auth management feature is
unusable end-to-end regardless of code. Migration 038 seed pattern will be
mirrored after approval (role_grants backfill like migration 063).

No other grants required: BS* slices gate on BILLING_READ/WRITE (held);
CS3/CS5-CS7 gate on PATIENT_READ / REPORT_READ / CARE_PLAN_WRITE /
ENCOUNTER_WRITE (all held).

## Implementation slices (TDD, RED→GREEN, one commit each)

### Billing
- **BS1 — B-12 suggestions fix + confidence**: pass proper procedure key +
  modality from queue rows; CodingService returns ranked candidates with
  confidence (match quality: exact desc > substring > icd-fallback); FE
  banner renders confidence %. Tests: coding map unit + queue integration.
- **BS2 — B-05 batch charge drop (+B-10 batch rework)**:
  `POST /ris/billing/charges/batch {charge_ids[], cpt_overrides?}` loops the
  audited drop path (BILLING_WRITE); `POST /ris/billing/claims/batch-resubmit
  {claim_ids[], note}` for reason-code groups. FE: row selection + batch bar
  in BillingQueue/DenialRework (Worklist batch-bar pattern).
- **BS3 — B-02/B-06 claims tracking**: `GET /ris/billing/claims
  ?status=&payer=&date_from=&date_to=` (BILLING_READ) + batch-submit
  `{claim_ids[]}` (BILLING_WRITE); FE Claims page `/billing/claims` with
  lifecycle tags, filters, drill-in history drawer (existing endpoint);
  sidebar item.
- **BS4 — B-03 responsibility endpoint**: `GET
  /ris/billing/patients/{id}/responsibility` (BILLING_READ) composing
  eligibility (copay/deductible/coinsurance placeholder), open charges total,
  invoice balances. FE lands with CS3 chart Billing tab.
- **BS5 — B-07 revenue dashboard**: `GET /ris/billing/revenue?days=` (clamped
  ≤90) returning daily collections trend, by-modality, by-payer, AR aging $
  buckets; FE page `/billing/revenue` with Statistic cards + tables; sidebar.
- **BS6 — B-11 export + billing landing**: client-side CSV export button on
  UnbilledAging; navigator LANDING_STEPS gains BILLING_READ step →
  `/billing/queue` (fixes cashier fall-through-to-/account).

### Care Coordinator
- **CS1 — CC-11 lifecycle fix + grant application**: apply approved G2 to
  MATRIX_B_COORD (+ role_grants migration); new `POST /ris/prior-auth/{id}/submit`
  wiring orphaned `submit_for_review()` (REQUIRED→PENDING);
  `POST /ris/prior-auth/{id}/override {reason}` → NOT_REQUIRED + audit;
  PriorAuthPanel: Submit-for-review action, Override action, Expiring-soon
  tab (wire unused listPriorAuthExpiring).
- **CS2 — CC-13 global search mount**: base.tsx mounts PatientSearchOverlay
  outside /frontdesk too (coordination + billing workspaces); sidebar
  Coordination section gains Patient Search trigger item.
- **CS3 — CC-09/CC-10 patient chart tabs**: Patient.tsx → Tabs (Demographics
  | Reports | Orders | Billing[BILLING_READ]); Reports rows show
  impression+recommendations excerpts (priors payload gains
  `recommendations_excerpt`) and click through to console/report; Orders tab
  uses existing `/ris/orders?patient=` filter.
- **CS4 — CC-12 per-patient opt-out**: migration 094
  `patient_reminder_optouts(patient_id, event_type NULL=all, opted_out_at,
  by)`; dispatch service skips opted-out patients; Reminders page per-row
  opt-out toggle + list.
- **CS5 — CC-02 care plans**: migration 095 `care_plans(patient_id, title,
  status CHECK active/completed/on_hold, tasks JSONB, responsible_provider,
  follow_up_at, tenant)`; CRUD `/api/ris/care-plans` gated CARE_PLAN_WRITE /
  READ-via-PATIENT_READ; FE `/care-plans` page (list + create/edit modal +
  status transitions).
- **CS6 — CC-03 encounters**: migration 096 `encounters(patient_id,
  encounter_type CHECK visit/call/message/fax, occurred_at, summary,
  linked_order_id, linked_report_id, recorded_by, tenant)`; GET list
  (patient-scoped) + POST (ENCOUNTER_WRITE); timeline rendered in chart
  Encounters tab (clone TrackingTimeline pattern).
- **CS7 — CC-04 communication log**: migration 097 `communications(patient_id,
  direction CHECK inbound/outbound, channel, category, summary,
  related_order_id, logged_by, tenant)`; POST + search-by-patient GET;
  FE `/communications` log page + quick-log action from chart.
- **CS8 — CC-01 test debt**: Orders.test.tsx covering derivedOrderStatus
  boundaries (>24h amber, >72h red), stuck-work counts, filters.

## Test strategy

Per spec §8: pytest async integration per slice (backend), Vitest+RTL per
surface (frontend), tsc+ruff gates, FULL suites before every commit, one
commit per feature. E2E Playwright critical paths, axe, k6, visual regression
remain deferred per standing convention.

## Deferred backlog

1. Configurable widget framework (platform ADR, unchanged).
2. B-04 ERA/835 posting into v2 ledger (must NOT spawn a third money model).
3. B-08 contract rates, B-09 fee-schedule versions/CMS import (P2).
4. CC-05 referrals, CC-06 discharge checklists, CC-07 FHIR MedicationRequest
   (external EMR dependency), CC-08 handoff notes (P2).
5. Real X12 837 serializer behind the claim stub (integration-dependent).
