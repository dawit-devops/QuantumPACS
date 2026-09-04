# pacs_admin — Frontend Inventory (Phase 5b)
Date: 2026-08-28 | Browser session: fresh login (no tenant — platform-side)
Skills invoked: antd, frontend-react-best-practices

## A. Needs backend wiring (UI exists, backend missing/incomplete)

None found. All 21 surfaces in pacs_admin's scope have fully-wired backend endpoints (verified via API walk + browser walk).

## B. Better omitted / reduced (overlaps, noise, unmaintained)

None found within pacs_admin's scope. The admin surfaces are well-maintained.

## C. Needs refinement (works but has gaps)

| # | Page | Route | Gap | Recommendation | Decision |
|---|---|---|---|---|---|
| C1 | Dashboard | /admin | KPI cards show "—" for platform-side users (test.pacs_admin tenant=NULL). The metrics endpoint returns empty aggregates because the platform DB has no tenant-scoped patients/studies. | KEEP (dev-seed limitation — not a bug). Tenant-scoped users (acme.*) would see real data. Not applicable for production. | KEEP |
| C2 | Billing Queue | /billing/queue | Shows "No unbilled charges — everything is captured" — correct empty state for the seeded data. The billing write buttons (drop, batch, submit) are expected to be hidden/disabled for BILLING_READ-only users. | KEEP (no change — correct behavior for BILLING_READ role). | KEEP |

## Summary
- 21 surfaces walked in browser: all PASS (render without errors)
- 0 console errors (only the expected 403 on /api/v2/tenants — no TENANT_READ)
- Clinical routes (/worklist, /exams, etc.) correctly redirect to /admin
- No orphaned backend routes within pacs_admin's scope
- The R1 grant additions (DICOMWEB_READ, HL7_READ, REPLICA_READ, ROUTING_READ) successfully unlock the DICOMweb, HL7, Interface Health, Replicas, and Routing surfaces — all render with live data