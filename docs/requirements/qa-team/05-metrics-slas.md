# Metrics & SLAs — Radiology & Imaging Service QI/QA Team (R05)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Performance Metrics (Frontend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R05-01 | QA queue load (LCP) | ≤ 2s | Lighthouse CI, RUM | Per release | Frontend |
| M-R05-02 | QA form submission latency | ≤ 500ms | Backend timing | Per release | Backend |
| M-R05-03 | Protocol save latency | ≤ 300ms | Backend timing | Per release | Backend |
| M-R05-04 | Incident log save latency | ≤ 500ms | Backend timing | Per release | Backend |
| M-R05-05 | Queue auto-refresh staleness | ≤ 1min | Synthetic probe (Grafana) | Continuous | Backend |
| M-R05-06 | Dashboard LCP | ≤ 2.5s | Lighthouse CI | Per release | Frontend |
| M-R05-07 | Dashboard widget data freshness | ≤ 5min | Synthetic probe | Continuous | Backend |
| M-R05-08 | Inline validation latency | ≤ 200ms | Frontend timing | Per release | Frontend |
| M-R05-09 | WCAG 2.2 AA audit score | 100% pass (0 violations) | axe-core CI | Per release | Frontend |
| M-R05-10 | Design token compliance | 100% (no one-off colors) | Stylelint custom rule | Per release | Frontend |

---

## Performance Metrics (Backend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R05-11 | API p95 latency (QA endpoints) | ≤ 300ms | k6 nightly | Nightly | Backend |
| M-R05-12 | QA queue query (50/page) | ≤ 200ms | Backend timing | Per release | Backend |
| M-R05-13 | QA score INSERT latency | ≤ 500ms | Backend timing | Per release | Backend |
| M-R05-14 | Concurrent QA reviewers | ≥ 10 | k6 WebSocket | Per release | QA |

---

## Clinical / QA Metrics (KPIs)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R05-15 | QA review turnaround (routine) | ≤ 24h | `qa_scores.reviewed_at` - `qa_queue.created_at` WHERE priority='routine' | Daily | QA Team |
| M-R05-16 | QA review turnaround (STAT) | ≤ 2h | Same, WHERE priority='stat' | Daily | QA Team |
| M-R05-17 | Protocol compliance rate | ≥ 95% per protocol | `qa_scores` pass_fail=true / total reviewed | Weekly | R03/R05 |
| M-R05-18 | Incident rate | ≤ 5% of exams | `incidents` count / total exams in period | Weekly | QA Team |
| M-R05-19 | Retake rate | ≤ 3% of exams | `incidents` WHERE `repeat_study_uid IS NOT NULL` | Weekly | QA Team |
| M-R05-20 | Corrective action resolution time | ≤ 7 days | `resolved_at` - `assigned_at` | Weekly | QA Team |
| M-R05-21 | QA queue backlog | ≤ 50 pending exams | `qa_queue` WHERE `status='pending'` | Daily | QA Team |
| M-R05-22 | QA form completion time | ≤ 3min per exam | User timing (performance.now) | Daily | QA Team |
| M-R05-23 | Peer review completion rate | ≥ 98% within 7 days | `peer_reviews` WHERE `completed_at ≤ assigned_at + 7 days` | Weekly | QA Team |
| M-R05-24 | Major discrepancy rate | ≤ 2% of peer reviews | `peer_reviews` WHERE `discrepancy_level IN ('major', 'critical')` | Weekly | QA Team |
| M-R05-25 | Protocol registry coverage | 100% active protocols have ACR benchmarks | All protocols have non-null `acr_benchmark` | Weekly | QA Lead |
| M-R05-26 | Dose outlier rate | ≤ 2% of exams | Studies exceeding DRL per protocol benchmark | Weekly | QA Team |
| M-R05-27 | Incident notification delivery | 100% within 1min | Notification timestamp vs incident log timestamp | Daily | Backend |
| M-R05-28 | Corrective action notification delivery | 100% within 1min | Notification timestamp vs corrective action creation | Daily | Backend |

---

## SLA Tiers

### Availability SLA

| Tier | Target | Scope | Measurement |
|------|--------|-------|-------------|
| **Critical (QA APIs)** | 99.9% | `/api/v2/qa/*` | Synthetic uptime monitor |
| **Non-Critical (Reports)** | 99.5% | `/api/v2/qa/reports/*` async jobs | Job success rate |
| **Maintenance Window** | Excluded | Scheduled maintenance (announced 72h prior) | Calendar |

### Support SLA

| Severity | Definition | Response Time | Resolution Target | Escalation |
|----------|-----------|---------------|-------------------|------------|
| **P1** | QA queue down; no review possible for >30min | ≤ 15min | ≤ 4h | On-call + QA Lead notified |
| **P2** | Single QA form failing; protocol CRUD broken | ≤ 4h | ≤ 24h | Ticket queue |
| **P3** | Cosmetic issue; slow but functional | ≤ 24h | ≤ 5 business days | Backlog |
| **P4** | Enhancement request | ≤ 5 business days | Next sprint | Backlog |

### Data Freshness SLA

| Data Type | Target | Mechanism | Monitoring |
|-----------|--------|-----------|------------|
| **QA Queue** | ≤ 1min | Auto-refresh polling | Synthetic probe checks last-update timestamp |
| **Protocol Registry** | ≤ 24h (changes propagate) | Manual refresh + cache invalidation | Daily check |
| **Corrective Actions** | ≤ 5min | Real-time notification | Grafana alert if staleness > 5min |
| **Incident Log** | Real-time | On submit | User confirmation |
| **Peer Review** | ≤ 7 days | Assignment + notification | Completion rate monitor |
| **QA Dashboard** | ≤ 5min | TanStack Query refetchInterval | Grafana alert if staleness > 5min |

### QA Review SLA

| Review Type | Target | Measurement |
|-------------|--------|-------------|
| **STAT exam QA** | ≤ 2h from queue entry to completed score | `qa_scores.reviewed_at` - `qa_queue.created_at` WHERE priority='stat' |
| **Routine exam QA** | ≤ 24h from queue entry to completed score | Same WHERE priority='routine' |
| **Peer review assignment** | ≤ 7 days from assignment to completion | `peer_reviews.completed_at` - `peer_reviews.assigned_at` |
| **Corrective action resolution** | ≤ 7 days from assignment to resolution | `corrective_actions.resolved_at` - `corrective_actions.assigned_at` |

---

## KPI Calculation Methods

### QA Review Turnaround (M-R05-15, M-R05-16)
```
turnaround = qa_scores.reviewed_at - qa_queue.created_at
```
- `qa_queue.created_at`: Timestamp when queue entry was created (R06 exam completion trigger)
- `qa_scores.reviewed_at`: Timestamp when QA reviewer submitted the score
- **STAT**: Queue entries with `priority='stat'`
- **p95**: 95th percentile of all turnaround times in measurement window

### Protocol Compliance Rate (M-R05-17)
```
compliance_pct = (passing_scores / total_reviewed_scores) × 100
```
- `passing_scores`: `qa_scores` WHERE `pass_fail=TRUE AND protocol_id=X AND reviewed_at >= period_start`
- `total_reviewed_scores`: `qa_scores` WHERE `protocol_id=X AND reviewed_at >= period_start`
- Target: ≥ 95% per protocol (ACR benchmark configurable per protocol)

### Incident Rate (M-R05-18)
```
incident_rate = (incident_count / total_exams) × 100
```
- `incident_count`: `incidents` WHERE `created_at >= period_start`
- `total_exams`: Count of studies completed in same period (from `qa_queue` completed entries)

### Retake Rate (M-R05-19)
```
retake_rate = (retake_count / total_exams) × 100
```
- `retake_count`: `incidents` WHERE `repeat_study_uid IS NOT NULL AND created_at >= period_start`

### Corrective Action Resolution Time (M-R05-20)
```
resolution_time = corrective_actions.resolved_at - corrective_actions.assigned_at
```
- Measured in days/hours
- Target: ≤ 7 days for all open actions

### Peer Review Completion Rate (M-R05-23)
```
completion_rate = (completed_reviews / total_assigned_reviews) × 100
```
- `completed_reviews`: `peer_reviews` WHERE `status='completed' AND completed_at ≤ assigned_at + 7 days`
- `total_assigned_reviews`: All `peer_reviews` assigned in measurement window

### Major Discrepancy Rate (M-R05-24)
```
discrepancy_rate = (major_critical_reviews / total_completed_reviews) × 100
```
- `major_critical_reviews`: `peer_reviews` WHERE `discrepancy_level IN ('major', 'critical') AND status='completed'`
- `total_completed_reviews`: All `peer_reviews` WHERE `status='completed'`

### Dose Outlier Rate (M-R05-26)
```
outlier_rate = (outlier_studies / total_dosed_studies) × 100
```
- `outlier_studies`: `qa_scores` WHERE `dose_dlp > protocol.acr_benchmark.max_dlp_mgycm` (or other benchmark exceeded)
- `total_dosed_studies`: All `qa_scores` with non-null dose values in measurement period

---

## Monitoring & Alerting (v3.0 — Basic)

| Signal | Alert Condition | Action | Recipient |
|--------|----------------|--------|-----------|
| QA API p95 > 500ms | Grafana alert | Auto-scale backend; investigate slow query | Backend team |
| QA queue LCP > 3s | Lighthouse CI failure | Block deploy; investigate frontend | Frontend team |
| Queue staleness > 5min | Prometheus probe | Restart refetch worker; investigate | Backend team |
| QA score INSERT > 1s | Backend timing metric | Investigate DB write performance | Backend team |
| Peer review completion < 90% | Weekly metric check | Notify QA Lead | QA Lead |
| Corrective action resolution > 7 days | Weekly metric check | Notify QA Lead + R03 | QA Lead + R03 |
| WCAG audit failure | axe-core CI gate | Block deploy; fix violation | Frontend team |

**Note**: Configurable threshold alerting (FR-R05-13 in v3.1) is deferred. v3.0 uses static thresholds above.

---

## Measurement Tools

| Tool | Purpose | Cadence |
|------|---------|---------|
| **Lighthouse CI** | LCP, TTI, CLS, INP, axe-core | Per release (GitHub Actions) |
| **k6** | API p95, concurrent users, load | Nightly + per release |
| **Playwright** | E2E QA review flows, keyboard tests | Per release + PR |
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
| **Daily** | QA Team | Queue backlog, review turnaround, incident count |
| **Weekly** | QA Lead + R03 | Protocol compliance, corrective action resolution, peer review completion, discrepancy rate |
| **Monthly** | QA Lead + Hospital Leadership | Compliance summary, incident trends, retake rate, dose outlier analysis |
| **Per Release** | Engineering + QA | Performance metrics; accessibility audit; bundle size; token compliance |
| **Quarterly** | QA Lead + Compliance | Audit log review; HIPAA minimum necessary verification; access review |