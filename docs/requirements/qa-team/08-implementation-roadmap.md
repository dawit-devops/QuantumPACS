# Implementation Roadmap — Qa Team (R05)

## Artifact Status Overview

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | done |
| 02 | Workflow Maps | `02-workflow-maps.md` | done |
| 03 | User Stories | `03-user-stories.md` | done |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done |
| 07 | Traceability Matrix | `07-traceability.md` | done |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done |

## FR/NFR Implementation Status

> **Codebase reality (verified 2026-08-03)**: the R05 QA module is implemented
> end-to-end — backend `api/qa.py` with routes in `api/routes.py`
> (`/qa/queue`, `/qa/reviews/{exam_id}`, `/qa/reviews`, `/qa/protocols`,
> `/qa/protocols/{id}`, `/qa/incidents`, `/qa/incidents/{id}/resolve`,
> `/qa/corrective-actions`, `/qa/corrective-actions/{id}/resolve`, `/qa/dashboard`,
> `/qa/reviewers`; plus `/peer-reviews` for R12), frontend `frontend/src/qa/`
> (QAQueue, QAReviewForm, ProtocolRegistry, Incidents, CorrectiveActions) with
> routes `/qa/queue`, `/qa/review/:examId`, `/qa/protocols`, `/qa/incidents`,
> `/qa/actions`, and the `qa_team` built-in role in `api/permissions.py`.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R05-01 | **QA Review Queue** — `GET /qa/queue`, `QAQueue.tsx` at `/qa/queue` (filters: modality/status/priority, pagination) | AC-R05-01..10 | M |
| FR-R05-02 | **QA Review Workflow** — `GET/PUT /qa/reviews/{exam_id}`, `POST /qa/reviews`, `QAReviewForm.tsx` at `/qa/review/:examId` (pass/fail, dose fields, sequence checklist) | AC-R05-11..20 | M |
| FR-R05-03 | **Protocol Registry CRUD** — `GET/POST /qa/protocols`, `GET/PUT/DELETE /qa/protocols/{id}`, `ProtocolRegistry.tsx` at `/qa/protocols` | AC-R05-21..33 | M |
| FR-R05-04 | **QA Score Persistence** — `qa_scores` write via review submit (protocol_id, dose, pass_fail, reviewed_by) | AC-R05-34..43 | S |
| FR-R05-05 | **Corrective Action Inbox** — `GET/POST /qa/corrective-actions`, `POST /qa/corrective-actions/{id}/resolve`, `CorrectiveActions.tsx` at `/qa/actions`; failed review auto-opens corrective action | AC-R05-44..54 | M |
| FR-R05-06 | **Incident/Retake Logging** — `GET/POST /qa/incidents`, `POST /qa/incidents/{id}/resolve`, `Incidents.tsx` at `/qa/incidents` | AC-R05-55..64 | M |
| FR-R05-07 | **RBAC QA Role** — `qa_team` built-in role in `permissions.py`: `QA_READ`, `QA_WRITE`, `PROTOCOL_MANAGE`, `PEER_REVIEW_*`, `DICOMWEB_READ`, `METRICS_READ` | AC-R05-65..71 | S |
| FR-R05-10 | **Peer Review Workflow** — `GET /qa/reviewers` (radiologist picker), `POST /peer-reviews` (assign), `POST /peer-reviews/{id}/submit` (R12 findings); `qa_team` has `PEER_REVIEW_*` perms | AC-R05-153 | M |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R05-08 | **Automated Dose Validation** (DRL flags on ingestion) | No rules engine; no dose baseline job | AC-R05-72..79 | L |
| FR-R05-09 | **DICOM Tag Validation Rules** (required-sequence auto-check) | No DICOM tag parser/rules engine | AC-R05-80..87 | L |
| FR-R05-11 | **ACR Phantom QA** (scheduled phantom scans, auto-analysis) | No phantom scheduling/analysis library; v3.1 scope | AC-R05-151 | L |
| FR-R05-12 | **Regulatory Reporting** (MQSA/ACR/state exports) | No reporting engine; v3.1 scope | AC-R05-152 | L |
| FR-R05-13 | **AI-assisted QA** (artifact detection) | No AI integration; v3.2 scope | — (no AC yet) | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Rules engine + ingestion-time hook (C-STORE) | FR-R05-08, FR-R05-09 | AC-R05-72..87 | Automated dose/tag validation — v3.1 backlog |
| Phantom QA analysis library | FR-R05-11 | AC-R05-151 | v3.1 backlog |
| Reporting engine (MQSA/ACR/state templates) | FR-R05-12 | AC-R05-152 | v3.1 backlog |
| AI inference integration | FR-R05-13 | — | v3.2 backlog |

## Next Steps (highest priority)

1. **Update roadmap each sprint** as FR/NFR status changes
2. **Plan FR-R05-08/09 (automated validation)** — rules engine + ingestion hook; v3.1 backlog
3. **Plan FR-R05-11/12 (phantom QA, regulatory reporting)** — v3.1 backlog
