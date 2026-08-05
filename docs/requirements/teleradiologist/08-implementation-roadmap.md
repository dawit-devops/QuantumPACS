# Implementation Roadmap — Teleradiologist (R18)

## Artifact Status Overview

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | done |
| 02 | Workflow Maps | `02-workflow-maps.md` | done |
| 03 | User Stories | `03-user-stories.md` | done |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done |
| 07 | Traceability Matrix | `07-traceability.md` | partial |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial |

## FR/NFR Implementation Status

> **Codebase reality (verified 2026-08-03)**: merge 4d136e0 shipped the R12
> reading/reporting stack shared by R18 — reading worklist (`/reports/reading-list`),
> structured reporting (draft → preliminary → final + sign + templates), peer
> review (`/peer-reviews*`), reading presets (`/reading-presets*`), notifications
> (`exam.completed` + `/ws`), plus SSO/OAuth/OIDC (`/oauth/*`) and tenant
> switching. Telerad-specific FRs (offline, escalation, consult, multi-site
> dashboard, mobile, prefetch, messaging) remain GATED.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R18-03 | Secure remote access via SSO (OAuth/OIDC) + multi-site tenant switching — `/oauth/login`, `/oauth/callback`, `/oauth/token`, `/oauth/providers`, OIDC discovery; `TenantSelector.tsx` + `/tenants*` | AC-R18-04-01, 03, 04, 05 | M |
| FR-R18-04 | Full DICOM viewer parity with R12 (shared `frontend/src/detail/*` surface, DICOMweb QIDO/WADO) | AC-R18-05-06 | M |
| FR-R18-05 | First-image load ≤ 2.5s over WAN — capability shipped; 10 Mbps throttle verification pending | AC-R18-05-01, 05 | L |
| FR-R18-07 | Preliminary report creation — draft → preliminary → final state machine + preliminary flow in `ReportEditor.tsx` | AC-R18-02-01, 02, 03, 04, 05 | L |
| FR-R18-08 | Escalate preliminary → final via `POST /reports/{exam_id}/sign` (REPORT_SIGN); per-site credential check not enforced | (covered by report-sign tests) | M |
| NFR-R18-03 | DICOM viewer first-image load (500-inst CT, WAN) — verifiable against shipped viewer | AC-R18-05-01 | L |
| NFR-R18-04 | Viewer interaction responsiveness (INP ≤ 200ms) | AC-R18-05-06 | L |
| NFR-R18-05 | Report autosave interval ≤ 10s — `ReportEditor.tsx` autosave loop | AC-R18-02-02 | M |
| NFR-R18-11 | VPN/SSO authentication time ≤ 3s — OAuth flow shipped; timing verification pending | AC-R18-04-03 | M |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R18-01 | Remote worklist — `GET /reports/reading-list` is priority-sorted with status/modality/search filters; site filter + assignment filter not built | No site/assignment-filtered teleradiology worklist view | AC-R18-01-01, 02, 03 | M |
| FR-R18-22 | Multi-monitor layout profiles — layout presets (1x1/1x2/2x2) per modality via `/reading-presets`; 3-monitor profiles not built | No 3-monitor profile config | AC-R18-10-03 | M |
| FR-R18-24 | Hanging protocol templates — W/L + layout presets per modality shipped (`STANDARD_WL`: Brain/Stroke/Bone/Lung/Mediastinum); scenario template set (chest CT, trauma pan-scan) not built | No scenario-based template catalog | AC-R18-10-05 | M |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R18-02 | Worklist freshness indicator | No freshness banner/polling UI | AC-R18-01-02, 05 | M |
| FR-R18-06 | Prefetch next 3 worklist studies | No prefetch endpoint/algorithm | AC-R18-05-02, 03, 04 | L |
| FR-R18-09 | Critical findings notification workflow | No escalation endpoint | AC-R18-03-01, 02, 03, 05 | L |
| FR-R18-10 | Critical finding + notification-method logging | No escalation/audit pipeline | AC-R18-03-02, 04 | M |
| FR-R18-11 | Consultation request/response | No consult endpoints (peer review is QA-style) | AC-R18-08-02 | L |
| FR-R18-12 | Voice dictation integration | No dictation plugin | AC-R18-07-01, 02 | L |
| FR-R18-13 | Offline study package download | No offline-package endpoints | AC-R18-07-03, 04 | L |
| FR-R18-14 | Offline draft sync | No offline mode (IndexedDB queue) | AC-R18-07-05 | L |
| FR-R18-15 | Multi-site dashboard | No per-site worklist-count dashboard | AC-R18-04-01, 02 | L |
| FR-R18-16 | Mark study "Consulted" | No consulted-state workflow | AC-R18-08-01, 02 | M |
| FR-R18-17 | Mobile viewer for urgent consultations | PWA exists; no telerad-specific mobile UI | AC-R18-09-01, 02 | L |
| FR-R18-18 | Prior studies side-by-side comparison | No priors endpoint (same gap as R12 FR-R12-06) | AC-R18-10-01, 02 | M |
| FR-R18-19 | Turnaround time per study | No per-study TAT metric in worklist | AC-R18-11-01, 02 | M |
| FR-R18-20 | STAT >20min overdue alert | No overdue-STUDY alerting | AC-R18-01-04 | M |
| FR-R18-21 | Secure messaging to referring clinician | Notifications exist; no clinician messaging | AC-R18-11-03, 04 | L |
| FR-R18-23 | Allergy/contrast reaction warnings | No allergy data pipeline | AC-R18-10-04 | M |
| NFR-R18-01 | Remote worklist load time | Blocked on FR-R18-01 site-filter work | — | L |
| NFR-R18-02 | Worklist real-time sync staleness ≤ 5s | `/ws` shipped; telerad worklist channel not wired | AC-R18-01-02, 05 | M |
| NFR-R18-06 | Offline study package generation | Blocked on FR-R18-13 | AC-R18-07-03 | L |
| NFR-R18-07 | Critical findings notification latency | Blocked on FR-R18-09/10 | AC-R18-03-02, 03 | L |
| NFR-R18-08 | System availability for remote access | Not yet scoped | AC-R18-04-02 | L |
| NFR-R18-09 | Session timeout for inactive remote sessions | No idle-timeout modal (token expiry only) | AC-R18-06-01, 02, 03 | M |
| NFR-R18-10 | Concurrent remote viewer sessions | Not yet scoped | — | L |
| NFR-R18-12 | Audit log retention ≥ 7 years | Not yet scoped | — | L |
| NFR-R18-13 | Bandwidth utilization for prefetch ≤ 30% | Blocked on FR-R18-06 | AC-R18-05-03 | L |
| NFR-R18-14 | Mobile viewer compatibility | Blocked on FR-R18-17 | AC-R18-09-02 | L |
| NFR-R18-15 | Keyboard accessibility | Viewer keyboard support exists; full-surface audit pending | AC-R18-05-06 | L |
| NFR-R18-16 | Screen reader support | Not yet scoped | — | L |
| NFR-R18-17 | TLS 1.3 only | TLS enforcement not verified | — | M |
| NFR-R18-18 | Geographic latency tolerance | Not yet scoped | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Critical-findings escalation endpoint + clinician-notification integration | FR-R18-09, 10, NFR-R18-07 | AC-R18-03-* | ACR 15-min critical-findings requirement cannot ship |
| Offline package generation (encrypted ZIP + job queue) | FR-R18-13, 14, NFR-R18-06 | AC-R18-07-03, 04, 05 | Connectivity-failure mitigation unavailable |
| Consultation workflow endpoints | FR-R18-11, 16 | AC-R18-08-* | Second-opinion workflow unavailable |
| Site/assignment-filtered teleradiology worklist | FR-R18-01, NFR-R18-01 | AC-R18-01-01, 02, 03 | Remote worklist lacks site/assignment context |
| Multi-site dashboard aggregates | FR-R18-15 | AC-R18-04-01, 02 | No per-site coverage visibility |
| Background prefetch algorithm + endpoint | FR-R18-06, NFR-R18-13 | AC-R18-05-02, 03, 04 | Wait-time reduction between studies unavailable |
| Priors endpoint (shared R12 gap) | FR-R18-18 | AC-R18-10-01, 02 | Prior-comparison workflow unavailable |
| Voice dictation plugin | FR-R18-12 | AC-R18-07-01, 02 | Efficiency feature unavailable |

## Next Steps (highest priority)

1. **Raise critical-findings escalation with backend** — unblocks FR-R18-09/10; L effort
2. **Confirm priors API decision (shared with R12)** — unblocks FR-R18-18; M effort
3. **Scope offline-package generation** — unblocks FR-R18-13/14; L effort
4. **Extend reading worklist with site/assignment filters** — unblocks FR-R18-01; M effort
5. **Update roadmap each sprint** as FR/NFR status changes
