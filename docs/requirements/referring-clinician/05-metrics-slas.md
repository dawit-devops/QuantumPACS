# Metrics & SLAs — Referring Clinician (R14)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Performance Metrics (Frontend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R14-01 | Share-link page LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R14-02 | Viewer first image load | ≤ 2s | Backend timing | Per release | Backend |
| M-R14-03 | Study list load (LCP) | ≤ 2s | Lighthouse CI, RUM | Per release | Frontend |
| M-R14-04 | Study list query p95 | ≤ 200ms | Backend timing | Per release | Backend |
| M-R14-05 | Study detail page load | ≤ 2.5s | Lighthouse CI | Per release | Frontend |
| M-R14-06 | Report panel render | ≤ 1s | Frontend timing | Per release | Frontend |
| M-R14-07 | Follow-up form submit latency | ≤ 500ms | Backend timing | Per release | Backend |
| M-R14-08 | SSO redirect time | ≤ 3s | Synthetic probe | Continuous | Backend |
| M-R14-09 | Notification delivery latency | ≤ 5min | Synthetic probe | Continuous | Backend |
| M-R14-10 | Mobile viewer LCP | ≤ 3s | Lighthouse CI | Per release | Frontend |
| M-R14-11 | Mobile viewer touch response | ≤ 100ms | Frontend timing | Per release | Frontend |
| M-R14-12 | WCAG 2.2 AA audit score | 100% pass (0 violations) | axe-core CI | Per release | Frontend |
| M-R14-13 | Design token compliance | 100% (no one-off colors) | Stylelint custom rule | Per release | Frontend |
| M-R14-14 | Share link page bundle size | ≤ 30KB (chunk) | Vite Bundle Analyzer | Per release | Frontend |

---

## Performance Metrics (Backend)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R14-15 | Share link lookup p95 | ≤ 100ms | Backend timing | Per release | Backend |
| M-R14-16 | Study query p95 (referred) | ≤ 200ms | Backend timing | Per release | Backend |
| M-R14-17 | SSO assertion validation | ≤ 500ms | Backend timing | Per release | Backend |
| M-R14-18 | Notification generation | ≤ 1s | Backend timing | Per release | Backend |
| M-R14-19 | Share link concurrent viewers | ≥ 50 | k6 load test | Per release | QA |
| M-R14-20 | Share link rate limit | ≤ 100 req/min per key | k6 load test | Per release | Backend |
| M-R14-21 | Study list query (25/page) | ≤ 200ms | Backend timing | Per release | Backend |
| M-R14-22 | Follow-up request INSERT | ≤ 500ms | Backend timing | Per release | Backend |

---

## Clinical / QA Metrics (KPIs)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R14-23 | Share link access success rate | ≥ 99.5% | `shared_files` successful accesses / total attempts | Daily | Backend |
| M-R14-24 | Share link expiry compliance | 100% within configured duration | `shared_files.expires_at` vs actual access time | Weekly | QA Team |
| M-R14-25 | SSO login success rate | ≥ 98% | Successful SSO logins / total attempts | Daily | Backend |
| M-R14-26 | SSO login failure rate | ≤ 2% | Failed SSO logins / total attempts | Daily | Backend |
| M-R14-27 | Notification delivery rate | ≥ 99% for email; ≥ 99.9% for in-app | Delivered / attempted | Daily | Backend |
| M-R14-28 | Follow-up request response time | ≤ 48h (average) | `followup_requests.reviewed_at` - `followup_requests.created_at` | Weekly | QA Team |
| M-R14-29 | Follow-up request approval rate | ≥ 80% | Approved / total requests | Weekly | QA Team |
| M-R14-30 | Share link revocation time | ≤ 5min | `shared_files.revoked_at` - revocation request | Weekly | QA Team |
| M-R14-31 | Critical findings alert delivery | ≤ 5min | Notification timestamp vs report sign-off timestamp | Daily | Backend |
| M-R14-32 | PHI exposure incidents | 0 | Audit log review for PHI in URLs/logs | Weekly | QA Lead |
| M-R14-33 | Share key collision rate | 0 | Duplicate share key attempts | Daily | Backend |
| M-R14-34 | Mobile viewer crash rate | ≤ 0.1% | Frontend error tracking (Sentry) | Daily | Frontend |
| M-R14-35 | Share link reuse after revocation | 0 | Attempts to access revoked share key | Daily | Backend |

---

## SLA Tiers

### Availability SLA

| Tier | Target | Scope | Measurement |
|------|--------|-------|-------------|
| **Critical (Share Link Access)** | 99.9% | `/api/v2/share/*` | Synthetic uptime monitor |
| **Critical (SSO Login)** | 99.9% | `/api/v2/auth/sso` | Synthetic uptime monitor |
| **Non-Critical (Follow-up)** | 99.5% | `/api/v2/followup/*` async jobs | Job success rate |
| **Maintenance Window** | Excluded | Scheduled maintenance (announced 72h prior) | Calendar |

### Support SLA

| Severity | Definition | Response Time | Resolution Target | Escalation |
|----------|-----------|---------------|-------------------|------------|
| **P1** | Share link access broken; no study view possible for >30min | ≤ 15min | ≤ 4h | On-call + QA Lead notified |
| **P2** | SSO login failing; single referring clinician blocked | ≤ 1h | ≤ 4h | Ticket queue |
| **P3** | Notification delay (>15min); slow but functional | ≤ 4h | ≤ 24h | Ticket queue |
| **P4** | Enhancement request (mobile viewer, follow-up UX) | ≤ 24h | Next sprint | Backlog |

### Data Freshness SLA

| Data Type | Target | Mechanism | Monitoring |
|-----------|--------|-----------|------------|
| **Share link access** | Real-time | On click | Synthetic probe checks last-access timestamp |
| **Study list** | ≤ 5min | TanStack Query refetchInterval | Grafana alert if staleness > 5min |
| **Notifications** | ≤ 5min | Real-time push via Redis Stream | Synthetic probe |
| **SSO token** | ≤ 1h | JWT expiry + refresh | Grafana alert if token expiry < 5min remaining |
| **Follow-up requests** | Real-time | On creation | User confirmation |
| **Share link revocation** | ≤ 5min | On revoke | Synthetic probe |

### Access SLA

| Access Type | Target | Measurement |
|-------------|--------|-------------|
| **Share link access** | ≤ 1s from click to viewer render | User timing (performance.now) |
| **SSO login** | ≤ 3s from IdP redirect to study list | Synthetic probe |
| **Study list load** | ≤ 2s LCP | Lighthouse CI |
| **Follow-up request submission** | ≤ 500ms backend response | Backend timing |

---

## KPI Calculation Methods

### Share Link Access Success Rate (M-R14-23)
```
success_rate = (successful_accesses / total_access_attempts) × 100
```
- `successful_accesses`: `shared_files` accesses returning HTTP 200
- `total_access_attempts`: All `shared_files` access attempts (200 + 404 + 429)
- Measurement window: 24 hours rolling

### SSO Login Success Rate (M-R14-25)
```
success_rate = (successful_logins / total_login_attempts) × 100
```
- `successful_logins`: SSO assertions validated and JWT issued
- `total_login_attempts`: All SSO login attempts (success + failure)

### Notification Delivery Rate (M-R14-27)
```
email_rate = (email_delivered / email_attempted) × 100
in_app_rate = (in_app_delivered / in_app_attempted) × 100
```
- `email_delivered`: Email successfully sent (SMTP 250 response)
- `in_app_delivered`: In-app notification created in DB

### Follow-up Request Response Time (M-R14-28)
```
response_time = followup_requests.reviewed_at - followup_requests.created_at
```
- Measured in hours
- Target: ≤ 48h average across all open requests
- p50 and p95 reported weekly

### Critical Findings Alert Delivery (M-R14-31)
```
delivery_time = notification.timestamp - report.signed_at
```
- Target: ≤ 5min
- Measured for all critical findings in measurement window

### PHI Exposure Incidents (M-R14-32)
```
incidents = count of audit log entries where PHI found in URL or log
```
- Target: 0 (zero tolerance)
- Checked via weekly audit log review

---

## Monitoring & Alerting (v3.0 — Basic)

| Signal | Alert Condition | Action | Recipient |
|--------|----------------|--------|-----------|
| Share link p95 > 500ms | Grafana alert | Investigate DB query; check index | Backend team |
| SSO redirect > 5s | Synthetic probe failure | Check IdP health; investigate | Backend team |
| Notification delivery > 15min | Grafana alert | Check Redis Stream; investigate | Backend team |
| Share link staleness > 5min | Prometheus probe | Restart refetch worker | Backend team |
| SSO login failure rate > 5% | Grafana alert | Check IdP; investigate auth | Backend team |
| PHI in URL detected | Audit log alert | Immediate investigation | QA Lead + Security |
| Share key collision | Audit log alert | Investigate key generation | Backend team |
| WCAG audit failure | axe-core CI gate | Block deploy; fix violation | Frontend team |

---

## Measurement Tools

| Tool | Purpose | Cadence |
|------|---------|---------|
| **Lighthouse CI** | LCP, TTI, CLS, INP, axe-core | Per release (GitHub Actions) |
| **k6** | API p95, concurrent users, load | Nightly + per release |
| **Playwright** | E2E share-link workflow, SSO login | Per release + PR |
| **axe-core** | WCAG 2.2 AA automated | Per release (CI gate) |
| **Coblis Simulator** | Color-blind palette verification | Per release (manual) |
| **Grafana** | Real-time metrics dashboard (staleness, p95, jobs) | Continuous |
| **Prometheus** | Metric scraping from `/api/v2/metrics` | Continuous |
| **Synthetic Probe** | Uptime monitor, freshness check | Continuous |
| **Vite Bundle Analyzer** | Bundle size per chunk | Per release |
| **Sentry** | Frontend error tracking (crash rate) | Continuous |

---

## Review Cadence

| Cadence | Reviewer | Content |
|---------|----------|---------|
| **Daily** | QA Team | Share link access success rate, SSO login rate, notification delivery |
| **Weekly** | QA Lead + R03 | Follow-up response time, approval rate, PHI exposure incidents |
| **Monthly** | QA Lead + Hospital Leadership | Access success trends, SSO reliability, critical findings alert delivery |
| **Per Release** | Engineering + QA | Performance metrics; accessibility audit; bundle size; token compliance |
| **Quarterly** | QA Lead + Compliance | Audit log review; HIPAA minimum necessary verification; access review |