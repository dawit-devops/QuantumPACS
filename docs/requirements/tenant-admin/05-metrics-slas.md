# Metrics & SLAs — Hospital IT / Tenant Admin (R02)

Tenant-scoped infra and admin-console SLOs. Clinical KPIs belong to R03/R05; R02 owns
tenant operations and isolation guarantees.

## Metrics

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R02-01 | Tenant admin page load (LCP) | ≤ 2.5s p75 desktop 4G | Lighthouse CI, RUM | Per release | Frontend |
| M-R02-02 | Admin interaction responsiveness (INP) | ≤ 200ms p75 | RUM / Lighthouse | Per release | Frontend |
| M-R02-03 | Tenant user/worklist/routing list first page | ≤ 2s p90 | Synthetic probe | Daily | Backend |
| M-R02-04 | Tenant audit query first page | ≤ 2s p90 | Synthetic probe | Daily | Backend |
| M-R02-05 | Worklist/station list freshness | ≤ 30s | Synthetic probe | Daily | Backend |
| M-R02-06 | Integration test (FHIR) round-trip | ≤ 5s | `POST /fhir/admin/test` probe | Weekly | Backend |
| M-R02-07 | Notification event → unread badge | ≤ 5s | Synthetic event probe | Daily | Backend |
| M-R02-08 | Bulk import validation (1,000 rows) | ≤ 10s | Load test | Per release | Frontend/Backend |
| M-R02-09 | Cross-tenant access denial | 100% denied + logged | API test matrix (2 tenants) | Per release | Backend |
| M-R02-10 | Tenant isolation under concurrent load | 10 admins, zero data mixing | Load test | Per release | Backend |
| M-R02-11 | Audit coverage of tenant mutations | 100% | Audit coverage test | Per release | Backend |
| M-R02-12 | Admin session idle timeout | 30 min | Config test | Per release | Backend |
| M-R02-13 | Tenant admin console availability | 99.9% | Uptime monitor | Monthly | Platform |

## SLA Tiers

| Tier | Scope | Availability | Response |
|------|-------|--------------|----------|
| P1 — critical | Tenant reading path, worklist, routing, auth | 99.9% | Response ≤ 15 min; fix ≤ 4h |
| P2 — major | Tenant integrations (HL7/FHIR), replicas degraded | 99.5% | Response ≤ 1h; fix ≤ 24h |
| P3 — minor | Admin console UX, reporting | 99% | Response ≤ 4h; fix next release |
| P4 — monitoring | Metrics dashboards | best effort | Next business day |

## Tenant Isolation Guarantees

- Cross-tenant request denial: 100% — measured by API test matrix across every R02
  endpoint (M-R02-09).
- Denied attempts audit-logged with actor and target tenant for R05 review.
- Escalation path: storage-level or cross-tenant incidents escalate to R01 (PACS
  admin) within the P1 window.

## Reporting Alignment

- R02 tenant SLOs roll up into R03 service-director dashboards (tenant availability,
  storage utilization).
- R05 QI/QA consumes tenant audit completeness (M-R02-11).
