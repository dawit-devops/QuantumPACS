# Metrics & SLAs — Radiology Service Director (R03)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Performance Metrics (Frontend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R03-01 | Dashboard LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R03-02 | Dashboard Time to Interactive (TTI) | ≤ 3s | Lighthouse CI | Per release | Frontend |
| M-R03-03 | Widget data freshness (auto-refresh) | ≤ 5min staleness | Synthetic probe (Grafana) | Continuous | Backend |
| M-R03-04 | Drill-through navigation latency | ≤ 1s | Playwright timing | Per release | Frontend |
| M-R03-05 | Heatmap render time (1,008 cells) | ≤ 1s | Performance trace | Per release | Frontend |
| M-R03-06 | Cumulative Layout Shift (CLS) | < 0.1 | Lighthouse CI | Per release | Frontend |
| M-R03-07 | Interaction to Next Paint (INP) | ≤ 200ms | RUM (web-vitals) | Continuous | Frontend |
| M-R03-08 | Dashboard bundle size (per tab chunk) | < 50KB gzipped | Vite bundle analysis | Per release | Frontend |

---

## Performance Metrics (Backend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R03-09 | API p95 latency (analytics endpoints) | ≤ 300ms | k6 nightly | Nightly | Backend |
| M-R03-10 | Export generation (10k rows CSV) | ≤ 30s | Backend timing | Per release | Backend |
| M-R03-11 | Export generation (PDF with charts) | ≤ 60s | Backend timing | Per release | Backend |
| M-R03-12 | Concurrent dashboard users | ≥ 20 | k6 WebSocket scenario | Per release | QA |
| M-R03-13 | Breach detection job (10k studies) | ≤ 10s per cycle | Background job timing | Continuous | Backend |
| M-R03-14 | WebSocket/SSE capacity update latency | ≤ 5s end-to-end | Application-level timing | Continuous | Backend |
| M-R03-15 | Report generation success rate | ≥ 99% | Job logs aggregation | Daily | Backend |

---

## Clinical / Service Metrics (KPIs)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R03-16 | STAT turnaround time (p95) | ≤ 30min | DB query: `report.signed_at` - `study.created` WHERE priority=STAT | Daily | Clinical Ops |
| M-R03-17 | Routine turnaround time (p95) | ≤ 24h | DB query: same WHERE priority=Routine | Daily | Clinical Ops |
| M-R03-18 | SLA breach detection latency | ≤ 5min from breach | Alert timestamp vs threshold crossing | Continuous | Backend |
| M-R03-19 | Modality utilization accuracy | ±2% vs RIS reported | RIS cross-check (R15 ORM) vs PACS scheduled count | Weekly | R15 Integration |
| M-R03-20 | Protocol compliance rate | ≥ 95% per protocol | QA score aggregation (R05) | Weekly | R05 QA Team |
| M-R03-21 | Dashboard availability | ≥ 99.9% (excluding maintenance) | Synthetic uptime monitor (Pingdom/UptimeRobot) | Monthly | DevOps |

---

## Accessibility & Quality Metrics

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R03-22 | WCAG 2.2 AA audit score | 100% pass (0 violations) | axe-core CI + manual review | Per release | Frontend |
| M-R03-23 | Color-blind palette compliance | 100% charts/widgets | Coblis simulator (protanopia, deuteranopia, tritanopia) | Per release | Design |
| M-R03-24 | Keyboard navigation coverage | 100% interactive widgets | Tab navigation test script (Playwright) | Per release | QA |
| M-R03-25 | Design token compliance | 100% (no one-off colors) | Stylelint custom rule + manual | Per release | Frontend |
| M-R03-26 | Audit log completeness | 100% dashboard events logged | Log audit query vs actual user sessions | Monthly | Compliance |

---

## SLA Tiers

### Availability SLA

| Tier | Target | Scope | Measurement | Penalty (if applicable) |
|------|--------|-------|-------------|------------------------|
| **Critical (Dashboard APIs)** | 99.9% | `/api/v2/analytics/*`, `/api/v2/reports/*` | Synthetic uptime monitor | Defined in vendor contract |
| **Non-Critical (Export)** | 99.5% | `/api/v2/reports/generate` async jobs | Job success rate | Best effort |
| **Maintenance Window** | Excluded | Scheduled maintenance (announced 72h prior) | Calendar | N/A |

### Support SLA

| Severity | Definition | Response Time | Resolution Target | Escalation |
|----------|-----------|---------------|-------------------|------------|
| **P1** | Dashboard down; no KPI visibility for >30min | ≤ 15min | ≤ 4h | On-call + Service Director notified |
| **P2** | Single widget failing; export broken | ≤ 4h | ≤ 24h | Ticket queue |
| **P3** | Cosmetic issue; slow but functional | ≤ 24h | ≤ 5 business days | Backlog |
| **P4** | Enhancement request | ≤ 5 business days | Next sprint | Backlog |

### Data Freshness SLA

| Data Type | Target | Mechanism | Monitoring |
|-----------|--------|-----------|------------|
| **Capacity Heatmap** | ≤ 5min | WebSocket/SSE push on `events:ingestion` | Synthetic probe checks last-update timestamp |
| **KPI Cards (Volume, Turnaround, Utilization)** | ≤ 5min | `useQuery` refetchInterval | Grafana alert if staleness > 5min |
| **Protocol Compliance** | ≤ 24h | Manual refresh + daily batch | Daily QA score aggregation |
| **SLA Breach List** | ≤ 1min | Background job (1-min cycle) | Job duration monitor |
| **Scheduled Reports** | N/A (on-demand) | User triggers generation | Job success rate |

### Export SLA

| Export Type | Record Count | Target | Timeout | Retry |
|-------------|-------------|--------|---------|-------|
| **CSV (any widget)** | ≤ 10,000 rows | ≤ 30s | 60s | 1 auto-retry, then manual |
| **CSV (any widget)** | ≤ 100,000 rows | ≤ 2min | 5min | Same |
| **PDF (with charts)** | ≤ 10,000 rows | ≤ 60s | 120s | Same |
| **PDF (with charts)** | ≤ 100,000 rows | ≤ 5min | 10min | Same |
| **Streaming** | Any | Begin download within 10s | — | User cancel available |

---

## KPI Calculation Methods

### Turnaround Time (M-R03-16, M-R03-17)
```
turnaround = report.signed_at - study.created
```
- `study.created`: Timestamp when first DICOM instance received via C-STORE or STOW-RS
- `report.signed_at`: Timestamp when radiologist signs final report (R12 workflow)
- **STAT**: Studies marked `priority=STAT` (HL7 OBR.27 or manual flag)
- **p95**: 95th percentile of all turnaround times in measurement window

### SLA Breach Detection (M-R03-18)
```
IF study.priority = 'STAT' AND (now() - study.created) > 30min AND report.signed_at IS NULL:
    breach_type = 'STAT', minutes_overdue = (now() - study.created - 30min)
IF study.priority = 'Routine' AND (now() - study.created) > 24h AND report.signed_at IS NULL:
    breach_type = 'Routine', minutes_overdue = (now() - study.created - 24h)
```
- Detection runs every 1 minute via background job
- Breach logged to `sla_breaches` table with study_uid, type, minutes_overdue, detected_at
- Alert fired via `events:notify` Redis Stream

### Modality Utilization (M-R03-19)
```
utilization_pct = (scheduled_count / capacity) × 100
```
- `scheduled_count`: Studies in `worklist_entries` WHERE status='scheduled' AND modality=X AND date=Y
- `capacity`: From `modality_capacity` config table (studies per timeslot per modality)
- Cross-check: R15 RIS sends ORM count; compare to PACS scheduled count; flag if delta > 2%

### Protocol Compliance Rate (M-R03-20)
```
compliance_pct = (passing_studies / total_reviewed_studies) × 100
```
- `passing_studies`: `qa_scores` WHERE pass_fail=TRUE AND protocol_id=X
- `total_reviewed_studies`: `qa_scores` WHERE protocol_id=X (in time window)
- Target: ≥ 95% per protocol (ACR benchmark configurable per protocol)

---

## Monitoring & Alerting (v3.0 — Basic)

| Signal | Alert Condition | Action | Recipient |
|--------|----------------|--------|-----------|
| Dashboard API p95 > 500ms | Grafana alert | Auto-scale backend; investigate slow query | Backend team |
| Dashboard LCP > 3s | Lighthouse CI failure | Block deploy; investigate frontend | Frontend team |
| Staleness > 10min | Prometheus probe | Restart refetch worker; investigate Redis Stream lag | Backend team |
| Breach detection job > 30s | Job duration metric | Investigate query performance; index check | Backend team |
| Export failure rate > 1% | Job log aggregation | Investigate storage backend; retry queue | Backend team |
| WCAG audit failure | axe-core CI gate | Block deploy; fix violation | Frontend team |

**Note**: Configurable threshold alerting (FR-R03-13) is deferred to v3.1. v3.0 uses static thresholds above.

---

## Measurement Tools

| Tool | Purpose | Cadence |
|------|---------|---------|
| **Lighthouse CI** | LCP, TTI, CLS, INP, axe-core | Per release (GitHub Actions) |
| **k6** | API p95, concurrent users, load | Nightly + per release |
| **Playwright** | Drill-through timing, E2E flows, keyboard tests | Per release + PR |
| **axe-core** | WCAG 2.2 AA automated | Per release (CI gate) |
| **Coblis Simulator** | Color-blind palette verification | Per release (manual) |
| **Grafana** | Real-time metrics dashboard (staleness, p95, jobs) | Continuous |
| **Prometheus** | Metric scraping from `/api/v2/metrics` | Continuous |
| **Synthetic Probe** | Uptime monitor, freshness check | Continuous |
| **Vite Bundle Analyzer** | Bundle size per chunk | Per release |

---

## Review Cadence

| Cadence | Reviewer | Content |
|---------|----------|---------|
| **Daily** | Service Director (R03) | KPI dashboard review; breach count; utilization outliers |
| **Weekly** | R03 + R05 QA | Protocol compliance; SLA breach trends; modality utilization vs capacity |
| **Monthly** | R03 + Hospital Leadership | Board report (from templates); capacity forecast; staffing adjustments; SLA summary |
| **Per Release** | Engineering + QA | Performance metrics; accessibility audit; bundle size; token compliance |
| **Quarterly** | R03 + Compliance | Audit log review; HIPAA minimum necessary verification; access review |