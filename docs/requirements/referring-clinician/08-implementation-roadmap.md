# Implementation Roadmap — Referring Clinician (R14)

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

> **Codebase reality (verified 2026-08-03)**: the referring clinician's access is
> exclusively the share-link viewer (`/view/:key`, `tempKey` mode — Image tab only,
> no sidebar, no mutations). OAuth/SSO provider management exists on the admin side
> (`/oauth/providers`), but a clinician-facing SSO portal does not. There is **no
> report retrieval, no study-status tracking, no results notification, and no
> clinician patient selector** — all depend on the R12 reporting backend.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R14-01 | **Share-link access** — `/view/:key` viewer, `tempKey` auth, 64-char hex key | AC-R14-01..08 | S |
| FR-R14-03 | **Image viewer** (scroll, WW/WL, zoom, annotate) via share link | AC-R14-15..21 | S |
| FR-R14-02 (partial) | **SSO/OIDC admin scaffolding** — OAuth providers CRUD exists; clinician login portal GATED | AC-R14-09..14 | M |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R14-04 | **Report retrieval** (structured + narrative report display) | `GET /reports/{exam_id}` exists behind REPORT_READ (radiologist only; not physician/share-link — re-verified post-merge 4d136e0); clinician-accessible report view still missing | AC-R14-22..27 | L |
| FR-R14-05 | **Study status tracking** (scheduled/in-progress/complete) | No clinician-facing status API | AC-R14-28..34 | M |
| FR-R14-06 | **Results notification** (email + in-app) | No notification routing to clinicians; email service | AC-R14-35..41 | M |
| FR-R14-07 | **Patient selector / search** for clinician | No clinician-scoped search portal | AC-R14-42..49 | L |
| FR-R14-08 | **Study detail view** (demographics + metadata) | Reuses patient page but no clinician portal shell | AC-R14-50..55 | M |
| FR-R14-09 | **Mobile-responsive viewer + report** | PWA exists; portal shell GATED | AC-R14-56..62 | M |
| FR-R14-10 | **Follow-up request** | No workflow endpoint | AC-R14-63..68 | L |
| FR-R14-11 | **Share link management** (clinician views own links) | Share creation is R01/R12-side today; no clinician self-service | AC-R14-69..74 | L |
| FR-R14-12 | **Critical findings alert** | Depends on R12 escalation endpoint | — | L |
| NFR-R14-01..12 | Perf, expiry, uniqueness, SSO latency, a11y, PHI, audit, rate limit | Blocked on the FRs above | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| R12 structured reporting (create/sign) | FR-R14-04 | AC-R14-22..27 | Report display impossible without report data |
| Clinician portal shell (routes + SSO) | FR-R14-05..09 | AC-R14-28..62 | Requires product decision + backend scoping |
| Notification/email service to external users | FR-R14-06 | AC-R14-35..41 | Email delivery to referring clinicians not wired |

## Next Steps (highest priority)

1. **Confirm share-link viewer as v3.0 slice** — ship FR-R14-01/03 (implemented) and
   defer portal FRs; S effort
2. **Raise reporting + notification requirements with backend** — unblocks FR-R14-04/06; L effort
3. **Update roadmap each sprint** as FR/NFR status changes
