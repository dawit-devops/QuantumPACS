# super_admin — Backend Feature Inventory (Phase 5a)

Date: 2026-08-27
Method: enumerate all routes in `backend/api/routes.py` (v1 + auto `v2` alias),
cross-reference against every frontend call site (`frontend/src/**`, via
`request()` / `useFetch` / raw `fetch` / `open()` / `wadors:`/`wadouri:` image
schemes). False negatives eliminated by direct grep of each candidate.

Skills invoked: security-fastapi, iam-audit, multi-tenant-saas, hipaa-compliance

## Cross-reference summary

- Backend routes registered: **344** (172 v1 + 172 auto-generated `/v2` aliases).
- Frontend call paths enumerated: **245** (dynamic segments normalized).
- Backend routes with no `request()`/fetch caller: **~35** after removing
  false negatives (routes the viewer/image-loader calls via `wadors:`/`wadouri:`
  URLs, `open()` downloads, and test-only callers).
- Categories below: **ORPHANED** (should be surfaced), **DUPLICATE/DEAD**
  (candidate for removal/consolidation), **INTERNAL** (no UI by design).

## ORPHANED — implemented in backend, no frontend surface

These are production-intent handlers the platform (and/or clinical) roles cannot
reach from the UI. Each needs a user decision: **WIRE / DEFER / REJECT**.

| # | Backend route | Handler | Tenant-scoped? | Why it should surface | Recommendation |
|---|---|---|---|---|---|
| O1 | `/equipment` `GET/POST`, `/equipment/{id}` `GET/PUT/DELETE` | EquipmentHandler, EquipmentItemHandler | per-tenant | Full equipment registry with NO UI at all (EQUIPMENT_READ/WRITE perms exist in roles.ts:171-172) | Build Equipment page (admin/technologist scope) |
| O2 | `/equipment/pm`, `/equipment/{id}/schedules`, `/equipment/schedules/{id}` | MaintenanceSchedulesHandler, MaintenanceScheduleItemHandler | per-tenant | PM (preventive maintenance) schedules — no UI | Fold into Equipment page |
| O3 | `/equipment/{id}/qc` | QCRecordsHandler | per-tenant | QC records — no UI | Fold into Equipment page |
| O4 | `/equipment/downtime/open`, `/equipment/{id}/downtime`, `/equipment/{id}/downtime/{id}` | EquipmentOpenDowntimeHandler, DowntimeEventsHandler, DowntimeEventHandler | per-tenant | Downtime tracking — no UI | Fold into Equipment page |
| O5 | `/equipment/reports/compliance`, `/equipment/reports/uptime`, `/equipment/reports/downtime-causes` | EquipmentReportsHandler | per-tenant | Compliance/uptime reports — no UI | Fold into Equipment page |
| O6 | `/equipment/{id}/contracts`, `/vendor-contracts/{id}` | VendorContractsHandler, VendorContractHandler | per-tenant | Vendor service contracts — no UI | Fold into Equipment page |
| O7 | `/work-orders`, `/work-orders/{id}`, `/parts`, `/parts/{id}` | WorkOrdersHandler, WorkOrderHandler, PartsInventoryHandler | per-tenant | Work orders + parts inventory — no UI | Fold into Equipment page |
| O8 | `/ris/billing/reconciliation` | RisReconciliationHandler (billing.py:1355) | per-tenant | Reconciliation page missing; sidebar has no Recon item | Add Reconciliation to Billing section |
| O9 | `/ris/billing/denials/import` `POST` | RisDenialImportHandler | per-tenant | Denial import (835/CSV) — Denial Rework page exists but no import | Add import action to Denial Rework |
| O10 | `/ris/patients/merge`, `/ris/patients/undo-merge` | RisPatientsMergeHandler, RisPatientsUndoMergeHandler | per-tenant | Patient merge — no UI (frontdesk/admin) | Add merge to Patient admin |
| O11 | `/ris/patients/{id}/check-in` | RisPatientCheckInHandler | per-tenant | Walk-in check-in (distinct from appointment check-in) — no UI | Wire to frontdesk check-in |
| O12 | `/ris/orders/{id}/history`, `/ris/orders/{id}/status` | RisOrderHistoryHandler, RisOrderStatusHandler | per-tenant | Order lifecycle detail — Order page only lists | Add history/status to Order detail |
| O13 | `/peer-reviews/reviewers` | PeerReviewReviewersHandler | per-tenant | Reviewer picker for peer-review assignment — no UI | Wire into peer-review assign |
| O14 | `/qa/reviewers` | QAReviewersHandler | per-tenant | QA reviewer picker — no UI | Wire into QA review |
| O15 | `/logs/event-types` | LogEventTypesHandler | n/a | Logs page filter source (frontend only calls `/logs` + `/logs/actors`) | Wire event-type filter into Logs |
| O16 | `/ris/scheduling/chargeback` | RisChargebackHandler | per-tenant | Schedule chargeback — no UI | Add to scheduling/billing |
| O17 | `/tenants/{id}/stats` | TenantStatsHandler | platform | Tenants page shows usage (`/tenants/{id}/usage`) but not stats | Fold into Tenants or mark superseded |
| O18 | `/reports/{id}/release` `PATCH` | ReportReleaseHandler | per-tenant | Report release gate — no caller found | Wire into report workflow (clinical) |
| O19 | `/portal/scope/{id}` `DELETE` | PortalScopeHandler | per-tenant | Portal scope removal — frontend only lists (`portal/scope`) | Add remove action to portal scope |

## DUPLICATE / DEAD — candidates for removal or consolidation

| # | Backend route | Handler | Category | Evidence | Recommendation |
|---|---|---|---|---|---|
| D1 | `/billing/*` (16 routes: pricing, invoices, invoices/{id}, invoices/{id}/claims, invoices/{id}/payments, invoices/{id}/plans, invoices/{id}/refunds, payments/{payment_id}/receipt, refunds, refunds/{id}, quotes, reconciliation, reconciliation/close, claims/{id}) | BillingPricingHandler, BillingInvoicesHandler, BillingInvoiceHandler, BillingClaimsHandler, BillingPaymentsHandler, BillingPaymentPlansHandler, BillingRefundsHandler, BillingReceiptHandler, BillingRefundHandler, BillingQuotesHandler, BillingReconciliationHandler, BillingClaimHandler | DEAD/legacy | Frontend now calls only `/ris/billing/*`; no caller of `/billing/*` anywhere | Remove legacy module or keep only if roadmap keeps invoice/quotes flows |
| D2 | `/insurance/{id}` | InsuranceHandler | DEAD/legacy | Superseded by `/patients/{id}/insurance` + `/ris/patients/{id}/insurance` | Remove or rewire |
| D3 | `/wado` | DicomWebWadoUri | DEAD/legacy | Viewer uses `wadors:`/`wadouri:`; `/wado` has no caller | Remove (or keep as compat if external clients rely) |
| D4 | `/files/download_token` | DownloadToken | DEAD | No caller; downloads use `/files/download.zip` / `.csv` | Remove |
| D5 | `/ris/corrective-actions`, `/ris/corrective-actions/{id}`, `/ris/corrective-actions/escalate` | CorrectiveActionListHandler, CorrectiveActionHandler, EscalationHandler | DUPLICATE | Frontend calls `/qa/corrective-actions` instead; two implementations | Consolidate — decide canonical handler/table |
| D6 | `/ris/protocols/{id}`, `/ris/protocols/{id}/default` | ProtocolHandler, ProtocolDefaultHandler | DUPLICATE | Frontend calls `/qa/protocols` (registry) + `/protocols` (exam); third `/ris/protocols` set | Consolidate — decide canonical registry |

## INTERNAL — no UI by design (excluded from walk)

- `.well-known/openid-configuration`, `/oauth/callback`, `/oauth/jwks`,
  `/oauth/token` — OIDC/OAuth flows (redirect-based).
- `/fhir/*` (metadata, Patient, ImagingStudy, DocumentReference, ServiceRequest,
  DiagnosticReport) — external FHIR API.
- `/hl7` (Hl7Receiver POST), `/mpps/events` — modality/HIS device integration.
- `/docs`, `/docs/openapi.json` — swagger UI.
- `/dicomweb/studies/{study_uid}`, `.../metadata`, `.../series/...`,
  `.../instances/...`, `.../frames/...`, `.../archive` — WADO-RS image paths
  consumed by Cornerstone via `wadors:`/`wadouri:` URLs (not `request()`), so
  they ARE in use but via the viewer, not a page.

## Verified-called (false negatives cleared)

Routes that appeared uncalled in the first pass but ARE used by the frontend:
`qa/dashboard` (QaOverview widget), `files/download.zip` + `files/download.csv`
(Files.tsx `open()`), `nursing/prep-list` (api/nursing.ts), `portal/scope` (list),
and the exam sub-resources `exams/{id}/identity-confirm`, `.../protocol`,
`.../acquisitions/{aid}/{decision}`, `.../safety-checks`, `.../incidents`,
`.../overrides` (technologist/ExamConsole.tsx).

## Tenant-scoping note

Most ORPHANED handlers read `effective_tenant` from the token (per-tenant data
plane); the two platform-level items (O17 `/tenants/{id}/stats`) are
platform-owned. No cross-tenant leak was observed in the already-walked surfaces.

## Open decision items (Phase 5a gate)

1. **Equipment module (O1–O7)** — largest gap: full backend, zero UI. Wire a page?
2. **Billing Reconciliation (O8)** and **Denial Import (O9)** — add to Billing?
3. **Patient merge / check-in (O10–O11)** — surface for frontdesk/admin?
4. **Reviewer pickers (O13–O14)** — wire into peer-review / QA?
5. **Legacy `/billing/*` + `/wado` + `/insurance/{id}` + `/files/download_token`
   (D1–D4)** — remove?
6. **Duplicate registries (D5–D6)** — consolidate corrective-actions + protocols?
7. Small orphans (O12, O15, O16, O17, O18, O19) — wire/defer/reject each.

## Decision gate — user decisions (2026-08-27)

| Item | Decision | Action |
|---|---|---|
| O1–O7 Equipment module | DEFER | Record as backlog item; no code change |
| O8 Reconciliation page | WIRE | Build Billing Reconciliation page (frontend) |
| O9 Denial import | WIRE | Add Denial Import action to Denial Rework page |
| O10–O11 Patient merge/check-in | DEFER | Log for frontdesk walk |
| O13–O14 Reviewer pickers | DEFER | Log for radiologist/QA walk |
| D1–D4 Legacy dead routes | AUDIT-THEN-DECIDE | Audit done: D2/D3 keep; D1/D4 dead but test-covered → DEFER removal (cleanup sprint) |
| D5–D6 Duplicate registries | DEFER | Log for cleanup sprint |
| O12, O15–O19 Small orphans | DEFER | Log per-role; wire logs/event-types in logs walk |

## Legacy-route audit (D1–D4) — backend-internal caller check

Grep of `backend/` for non-route references (2026-08-27):

| Route | Backend-internal refs | Verdict |
|---|---|---|
| `/billing/*` (D1, 16 routes) | Only `routes.py` registration + `test_billing_api.py` (unit tests) + `test_rbac_enforcement.py` (fixture). No production caller. | DEAD in prod but test-covered → removal pending user decision below |
| `/insurance/{id}` (D2) | Same `InsuranceHandler` also registered at `/patients/{id}/insurance` (frontend-active). Only the `/insurance/{id}` alias is unused. | NOT dead — duplicate alias of an active handler |
| `/wado` (D3) | `dicomweb_proxy.py` (maps to `/aets/{ae}/wado` for DCM4CHEE), `dicomweb_logging.py` (wado_uri category), `dicomweb_admin.py` (known endpoint), + tests | NOT dead — standards WADO-URI endpoint (external DICOM clients) |
| `/files/download_token` (D4) | Only `routes.py` + `test_files.py` | DEAD in prod, test-covered |

### Audit conclusion

- D3 `/wado` and D2 `/insurance/{id}` should be **KEPT** (corrected from my earlier
  "dead" classification — they are standards/integration surface).
- D1 legacy `/billing/*` and D4 `/files/download_token` are dead in production but
  covered by unit tests. Removing them means deleting the legacy `billing.py`
  handlers + `test_billing_api.py` + `test_files.py::TestDownloadToken`. This is a
  self-contained cleanup but touches tested code — **pending user decision below**.
