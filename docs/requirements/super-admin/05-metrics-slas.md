# Metrics & SLAs — Super Admin (R01)

Infrastructure and admin-console SLOs. Clinical KPIs (report turnaround, etc.) belong
to R03/R05; R01 owns availability and platform operations.

## Metrics

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R01-01 | Admin console page load (LCP) | ≤ 2.5s p75 desktop, 4G | Lighthouse CI, RUM | Per release | Frontend |
| M-R01-02 | Admin interaction responsiveness (INP) | ≤ 200ms p75 | RUM / Lighthouse | Per release | Frontend |
| M-R01-03 | List first-page response (users/roles/tenants/logs) | ≤ 2s p90 | Synthetic probe with seeded volume | Daily | Backend |
| M-R01-04 | Audit log query (1M rows, filtered) | ≤ 2s p90 first page | Synthetic probe | Daily | Backend |
| M-R01-05 | Tenant provisioning end-to-end | ≤ 60s p95 | Instrumented timing on `POST /tenants` | Weekly | Backend |
| M-R01-06 | Worklist/replica status staleness | ≤ 30s | Synthetic probe | Daily | Backend |
| M-R01-07 | Notification event → unread badge | ≤ 5s | Synthetic event probe | Daily | Backend |
| M-R01-08 | Webhook test delivery | ≤ 5s with structured result | `POST /webhooks/test` probe | Weekly | Backend |
| M-R01-09 | Integration test (FHIR) round-trip | ≤ 5s | `POST /fhir/admin/test` probe | Weekly | Backend |
| M-R01-10 | Bulk import validation (1,000 rows) | ≤ 10s | Load test | Per release | Frontend/Backend |
| M-R01-11 | Audit coverage of admin mutations | 100% | Audit coverage test | Per release | Backend |
| M-R01-12 | Admin session idle timeout | 30 min | Config test | Per release | Backend |
| M-R01-13 | Concurrent super-admin sessions | ≥ 10 | Load test | Per release | Backend |
| M-R01-14 | Admin console availability | 99.9% | Uptime monitor | Monthly | Platform |

## SLA Tiers

| Tier | Scope | Availability | Response |
|------|-------|--------------|----------|
| P1 — critical | Reading path, storage, DICOM routing, auth | 99.9% | Incident response ≤ 15 min; fix ≤ 4h |
| P2 — major | Integrations (HL7/FHIR/OAuth), replicas degraded | 99.5% | Response ≤ 1h; fix ≤ 24h |
| P3 — minor | Admin console cosmetic/UX, reporting | 99% | Response ≤ 4h; fix next release |
| P4 — monitoring | Metrics dashboards, non-critical alerts | best effort | Next business day |

## Alerting & Notification SLAs

- Replica failure / integration outage → notification to super admin ≤ 5s of detection (M-R01-07).
- Critical-area metric threshold breach flagged on dashboard in real time (amber/red).
- Alerts must include drill-down context: affected tenant, resource, time window.

## Reporting Alignment

- R01 infra SLOs feed R03 service-director dashboards (availability, storage utilization).
- R05 QA consumes audit log completeness (M-R01-11) as an input to compliance reviews.
