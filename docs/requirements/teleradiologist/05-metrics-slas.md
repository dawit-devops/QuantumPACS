# Metrics & SLAs — Teleradiologist (R18)

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## Performance Metrics

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-01 | Multi-site dashboard load time | LCP ≤ 2.0s, INP ≤ 200ms | Lighthouse CI from remote IP (10 Mbps throttle) | Per release | Frontend | RUM + Synthetic |
| M-R18-02 | Site-switching latency (JWT token exchange + worklist load) | ≤ 2.5s p95 | Playwright E2E timing from dashboard click to worklist display | Daily | Backend + Frontend | APM |
| M-R18-03 | Worklist real-time sync staleness | ≤ 5s from exam completion to worklist appearance | WebSocket message timestamp delta vs DB trigger timestamp | Continuous | Backend | RUM |
| M-R18-04 | DICOM viewer first-image load (500-inst CT, WAN) | ≤ 2.5s p95 | Playwright + network throttle (10 Mbps, 50ms latency) | Per release | Frontend + Infra | Synthetic |
| M-R18-05 | DICOM viewer first-image load (cache hit) | ≤ 1.0s p95 | Playwright with pre-warmed cache | Per release | Frontend | Synthetic |
| M-R18-06 | DICOM viewer interaction responsiveness (pan/zoom/scroll) | INP ≤ 200ms p95 | Cornerstone3D event timing, RUM | Continuous | Frontend | RUM |
| M-R18-07 | Report autosave latency | ≤ 300ms p95 | TanStack Query mutation timing | Continuous | Backend | APM |
| M-R18-08 | Report autosave interval | Every 10s idle | Frontend timer log | N/A | Frontend | N/A |
| M-R18-09 | Preliminary report sign action | ≤ 500ms p95 | API response time for `POST /api/v2/reports/{id}/finalize` | Continuous | Backend | APM |
| M-R18-10 | Critical finding notification latency | ≤ 30s from report save to clinician notification delivery | Audit log timestamp delta (report signed → notification sent) | Per incident | Backend + Integration | Audit Dashboard |
| M-R18-11 | Critical finding escalation failure rate | <5% of automated notifications | Count(failed notifications) / Count(total notifications) | Weekly | Backend + Integration | Ops Dashboard |
| M-R18-12 | Offline study package generation time (500-inst study) | ≤ 30s p95 | Background job timing (queue → ZIP ready) | Per request | Backend | Job Queue Monitor |
| M-R18-13 | Offline study package size (500-inst study) | ≤ 2GB | ZIP file size measurement | Per request | Backend | Job Queue Monitor |
| M-R18-14 | Session timeout idle duration | 15min idle → warning, 16min → logout | Frontend idle timer log | N/A | Frontend | N/A |
| M-R18-15 | Session timeout warning response time | 60s countdown | Frontend timer | N/A | Frontend | N/A |
| M-R18-16 | JWT token refresh latency | ≤ 500ms p95 | `POST /api/auth/refresh` response time | Continuous | Backend | APM |
| M-R18-17 | Bandwidth prefetch utilization | ≤ 30% of available bandwidth during active viewing | Network monitor (navigator.connection API) | Continuous | Frontend | RUM |
| M-R18-18 | Prefetch cache hit rate | ≥ 70% of next-study opens are cache hits | Count(cache hits) / Count(study opens) | Weekly | Frontend | Analytics |
| M-R18-19 | Mobile worklist load time | LCP ≤ 3.0s over 4G | Lighthouse CI mobile throttle | Per release | Frontend | Synthetic |
| M-R18-20 | Mobile viewer first-image load (low resolution) | ≤ 5.0s p95 over 4G | Playwright + 4G throttle | Per release | Frontend | Synthetic |

---

## Clinical Workflow Metrics (Quality of Service)

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-21 | STAT study turnaround time (assignment → preliminary report signed) | ≤ 30min for 90% of cases | DB query: `reports.signed_at - studies.assigned_at` WHERE priority='STAT' | Real-time | Clinical Ops | QA Dashboard (R05) |
| M-R18-22 | Routine study turnaround time (assignment → preliminary report signed) | ≤ 4h for 90% of cases | DB query: `reports.signed_at - studies.assigned_at` WHERE priority='routine' | Daily | Clinical Ops | QA Dashboard (R05) |
| M-R18-23 | Critical finding communication latency (finding ID → clinician notification) | ≤ 15min for 95% of cases | DB query: `critical_findings.clinician_notified_at - critical_findings.created_at` | Per incident | Clinical Ops | Audit Dashboard |
| M-R18-24 | Preliminary report discrepancy rate (preliminary vs final) | <10% major discrepancies | Count(QA events WHERE type='discrepancy' AND severity='major') / Count(preliminary reports) | Weekly | QA Team (R05) | QA Dashboard |
| M-R18-25 | Preliminary report finalization latency (preliminary signed → final signed by R12) | ≤ 24h for 95% of cases | DB query: `reports.finalized_at - reports.signed_at` WHERE type='preliminary' | Daily | Clinical Ops | QA Dashboard |
| M-R18-26 | Consultation response time (routine) | ≤ 4h for 90% of cases | DB query: `consultations.completed_at - consultations.created_at` WHERE priority='routine' | Weekly | Clinical Ops | Performance Dashboard |
| M-R18-27 | Consultation response time (urgent) | ≤ 1h for 95% of cases | DB query: `consultations.completed_at - consultations.created_at` WHERE priority='urgent' | Weekly | Clinical Ops | Performance Dashboard |
| M-R18-28 | Studies read per teleradiologist per shift (8h) | 10-15 studies (baseline productivity) | Count(reports WHERE author=teleradiologist_id AND shift=current) / 8h | Per shift | Clinical Ops | Performance Dashboard |
| M-R18-29 | Remote access session duration | Median 8h (full shift coverage) | DB query: `audit_logs.logout_at - audit_logs.login_at` | Weekly | Security + Ops | Audit Dashboard |
| M-R18-30 | Remote access success rate (login → worklist load) | ≥ 99% success | Count(successful logins) / Count(login attempts) | Daily | Ops + Security | Ops Dashboard |

---

## System Availability & Reliability SLAs

| ID | SLA | Target | Measurement | Frequency | Owner | Escalation |
|----|-----|--------|-------------|-----------|-------|------------|
| SLA-R18-01 | Remote worklist availability | ≥ 99.95% uptime (excl. scheduled maintenance) | Synthetic uptime monitor from 3 geo locations (5min interval) | Continuous | Ops | P1 incident if <99.9% in 30-day window |
| SLA-R18-02 | DICOM viewer availability | ≥ 99.95% uptime | Synthetic viewer load test (5min interval) | Continuous | Ops | P1 incident if down >15min |
| SLA-R18-03 | Critical finding notification delivery | ≥ 99% delivery success | Count(delivered notifications) / Count(total notifications) | Per incident | Ops + Integration | P0 incident if delivery fails |
| SLA-R18-04 | SSO authentication availability | ≥ 99.9% uptime | OAuth provider status + fallback auth | Continuous | Security + Ops | P1 incident if SSO down >30min |
| SLA-R18-05 | WebSocket live update availability | ≥ 99% connection success | Connection success rate from client telemetry | Continuous | Backend | P2 incident if <95% success |
| SLA-R18-06 | Offline package generation success rate | ≥ 95% success | Count(successful jobs) / Count(queued jobs) | Weekly | Backend | P2 incident if <90% success |
| SLA-R18-07 | Database failover time (per-tenant DB outage) | ≤ 30s automatic failover | DB replica promotion time | Per incident | Infra | P1 incident if >1min |
| SLA-R18-08 | CDN/edge cache hit rate (DICOM images) | ≥ 80% cache hits | CDN analytics | Daily | Infra | P2 incident if <70% cache hit |
| SLA-R18-09 | API error rate (5xx errors) | <1% of requests | APM error tracking | Continuous | Backend | P1 incident if >2% error rate |
| SLA-R18-10 | Session timeout enforcement | 100% enforcement (no sessions >4h without re-auth) | Security audit log | Daily | Security | P0 incident if policy violated |

---

## Security & Compliance Metrics

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-31 | Remote access audit log completeness | 100% of remote sessions logged | Count(audit_logs) vs Count(JWT tokens issued) | Daily | Security | Audit Dashboard |
| M-R18-32 | PHI access audit retention | 7 years minimum | Audit log retention policy check | Quarterly | Compliance | Compliance Dashboard |
| M-R18-33 | Session timeout compliance | 100% of idle sessions logged out after 16min | Count(timeout events) vs Count(idle sessions >16min) | Daily | Security | Security Dashboard |
| M-R18-34 | MFA enforcement rate (remote access) | 100% of remote logins require MFA | Count(MFA logins) / Count(remote logins) | Daily | Security | Security Dashboard |
| M-R18-35 | Offline package encryption compliance | 100% of packages AES-256 encrypted | Audit log flag check | Per download | Security | Audit Dashboard |
| M-R18-36 | Critical finding audit completeness | 100% of critical findings have communication log | Count(critical_findings WITH notification_log) / Count(critical_findings) | Weekly | Compliance | Audit Dashboard |
| M-R18-37 | Suspicious activity detection rate | ≥ 95% of impossible travel scenarios detected | Security alert count vs manual audit | Monthly | Security | Security Dashboard |
| M-R18-38 | TLS version compliance (remote access) | 100% TLS 1.3, 0% legacy TLS | Web server access log analysis | Weekly | Security | Security Dashboard |
| M-R18-39 | Failed login lockout enforcement | 100% of accounts locked after 5 failed attempts | Security policy enforcement log | Daily | Security | Security Dashboard |
| M-R18-40 | Geolocation logging accuracy | ≥ 95% of remote sessions have geolocation | Count(audit_logs WITH geo) / Count(remote sessions) | Weekly | Security | Audit Dashboard |

---

## User Experience Metrics (Satisfaction & Usability)

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-41 | Teleradiologist satisfaction score (NPS) | ≥ 50 (promoters > detractors) | Quarterly survey | Quarterly | Product | UX Dashboard |
| M-R18-42 | Worklist usability score (ease of finding STAT studies) | ≥ 4.5/5 | Quarterly survey | Quarterly | Product | UX Dashboard |
| M-R18-43 | Viewer performance satisfaction | ≥ 4.0/5 | Quarterly survey | Quarterly | Product | UX Dashboard |
| M-R18-44 | Session timeout friction (unexpected logouts) | <5 incidents per teleradiologist per month | Support ticket analysis | Monthly | Product | Support Dashboard |
| M-R18-45 | Critical finding workflow clarity | ≥ 4.5/5 | Quarterly survey | Quarterly | Product | UX Dashboard |
| M-R18-46 | Multi-site context switching ease | ≥ 4.0/5 | Quarterly survey | Quarterly | Product | UX Dashboard |
| M-R18-47 | Offline package usage rate | ≥ 10% of teleradiologists use monthly | Feature usage analytics | Monthly | Product | Analytics Dashboard |
| M-R18-48 | Support ticket volume (teleradiology-specific issues) | <2 tickets per teleradiologist per month | Support ticket tagging | Monthly | Support | Support Dashboard |
| M-R18-49 | Training time for new teleradiologists | ≤ 2h to complete first study | Onboarding analytics | Per new user | Training | Training Dashboard |
| M-R18-50 | Mobile fallback usage rate | <5% of total reads (emergency use only) | Device type analytics | Monthly | Product | Analytics Dashboard |

---

## Resource Utilization Metrics

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-51 | Concurrent remote viewer sessions per teleradiologist | ≤ 3 simultaneous studies | WebSocket connection count per user | Continuous | Backend | Ops Dashboard |
| M-R18-52 | Bandwidth consumption per teleradiologist per shift | ≤ 20GB per 8h shift | Network egress monitoring | Per shift | Infra | Ops Dashboard |
| M-R18-53 | Database connection pool utilization (per-tenant) | ≤ 80% of pool size | DB connection metrics | Continuous | Backend | APM |
| M-R18-54 | Background job queue depth (offline packages) | ≤ 50 pending jobs | Job queue monitoring | Continuous | Backend | Ops Dashboard |
| M-R18-55 | Storage utilization (offline packages) | ≤ 500GB total | File storage metrics | Daily | Infra | Ops Dashboard |
| M-R18-56 | CDN bandwidth cost per teleradiologist per month | ≤ $50 per user | CDN billing analytics | Monthly | Finance + Ops | Finance Dashboard |
| M-R18-57 | Notification service cost per critical finding | ≤ $0.10 per SMS/page | Twilio/PagerDuty billing | Monthly | Finance + Ops | Finance Dashboard |
| M-R18-58 | CPU utilization (backend API) during peak hours | ≤ 70% average | Server metrics | Continuous | Backend | APM |
| M-R18-59 | Memory utilization (frontend viewer) | ≤ 2GB per tab | Browser memory profiling | Per release | Frontend | Synthetic |
| M-R18-60 | Prefetch cache storage per user | ≤ 5GB (IndexedDB quota) | Browser storage API | Continuous | Frontend | RUM |

---

## Operational Excellence Metrics

| ID | Metric | Target | Measurement | Frequency | Owner | Dashboard |
|----|--------|--------|-------------|-----------|-------|-----------|
| M-R18-61 | Incident response time (P0 critical finding notification failure) | ≤ 15min from alert to resolution | PagerDuty incident timeline | Per incident | Ops | Incident Dashboard |
| M-R18-62 | Incident response time (P1 worklist/viewer down) | ≤ 30min from alert to resolution | PagerDuty incident timeline | Per incident | Ops | Incident Dashboard |
| M-R18-63 | Mean time to recovery (MTTR) for teleradiology services | ≤ 1h | Incident duration average | Monthly | Ops | Ops Dashboard |
| M-R18-64 | Change failure rate (deployments breaking teleradiology features) | <5% of deployments | Deployment vs rollback count | Monthly | DevOps | DevOps Dashboard |
| M-R18-65 | Deployment frequency (teleradiology features) | ≥ 1 per 2 weeks | Git release tags | Monthly | DevOps | DevOps Dashboard |
| M-R18-66 | Code coverage (teleradiology-specific backend) | ≥ 80% | pytest --cov | Per commit | Backend | CI Dashboard |
| M-R18-67 | Code coverage (teleradiology-specific frontend) | ≥ 60% | Vitest coverage | Per commit | Frontend | CI Dashboard |
| M-R18-68 | E2E test coverage (teleradiology critical paths) | ≥ 10 Playwright specs | Test suite count | Per release | QA | CI Dashboard |
| M-R18-69 | Security scan findings (OWASP ZAP high-risk) | 0 high-risk findings | CI security gate | Per commit | Security | Security Dashboard |
| M-R18-70 | Dependency vulnerability findings (critical CVEs) | 0 critical CVEs | pip-audit + npm audit | Daily | Security | Security Dashboard |

---

## SLA Tier Definitions

### Tier 1: Critical (99.95% Availability)
- Remote worklist availability (SLA-R18-01)
- DICOM viewer availability (SLA-R18-02)
- Critical finding notification delivery (SLA-R18-03)

**Consequence of breach**: Teleradiologist cannot perform primary job function; patient care delayed; potential adverse outcomes.

**Escalation**: P0 incident, immediate on-call page, executive notification within 30min if unresolved.

**Financial penalty**: Service credit or refund per hospital contract (typically 10% monthly fee per 1h of downtime).

### Tier 2: High (99.9% Availability)
- SSO authentication availability (SLA-R18-04)
- WebSocket live update availability (SLA-R18-05)
- Database failover time (SLA-R18-07)

**Consequence of breach**: Degraded experience; workaround available (e.g., polling fallback, password login).

**Escalation**: P1 incident, on-call notification, executive notification if >4h downtime.

**Financial penalty**: Service credit per contract (typically 5% monthly fee per 4h of downtime).

### Tier 3: Medium (99% Availability)
- Offline package generation success rate (SLA-R18-06)
- CDN/edge cache hit rate (SLA-R18-08)
- API error rate (SLA-R18-09)

**Consequence of breach**: Feature unavailable or slow; core reading workflow unaffected.

**Escalation**: P2 incident, business hours support, no executive notification unless persistent.

**Financial penalty**: None (best-effort service level).

---

## Measurement & Reporting

### Real-Time Monitoring (Operational Dashboard)
- **Tool**: Grafana with Prometheus backend
- **Refresh**: 30s
- **Alerts**: PagerDuty integration for SLA breaches
- **Access**: Ops team, DevOps, Security

### Business Metrics (Executive Dashboard)
- **Tool**: Metabase or Tableau
- **Refresh**: Daily batch (midnight)
- **Reports**: PDF export, email digest
- **Access**: Clinical leadership (R03), QA team (R05), Product, Finance

### Audit Dashboard (Compliance)
- **Tool**: Custom Django admin panel + Elasticsearch/Kibana
- **Refresh**: Real-time (audit log stream)
- **Retention**: 7 years
- **Access**: Compliance officers, Security team, Auditors (read-only)

### User-Facing Dashboard (Teleradiologist Performance)
- **Tool**: React frontend with Chart.js
- **Refresh**: Real-time for current shift, daily batch for historical
- **Privacy**: Each teleradiologist sees only their own metrics
- **Access**: Individual teleradiologists (R18), supervising radiologists (R12), QA team (R05)

---

## Open Questions

1. **Metric baseline establishment**: What is current baseline for turnaround time and discrepancy rate before teleradiology launch?
2. **SLA breach notification**: Who receives executive notification — hospital CMO, radiology director, or PACS admin?
3. **Financial penalties**: Are service credits automatic or require hospital request?
4. **Benchmark targets**: Are targets based on ACR guidelines, peer hospitals, or internal historical data?
5. **Mobile usage policy**: Is mobile reading for diagnostics prohibited (emergency consultation only), or allowed with disclaimer?
6. **Prefetch bandwidth cap**: Should prefetch be disabled if user is on metered connection (cellular tether)?
7. **Offline package retention**: How long should generated packages be available for download (24h? 7 days? until user deletes)?
