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
| 07 | Traceability Matrix | `07-traceability.md` | partial |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial |

## FR/NFR Implementation Status

> **Codebase reality (verified 2026-08-03)**: none of the QA-specific features below
> exist in the frontend (`frontend/src/`) or backend (`backend/api/routes.py`). No
> `/qa/*` routes, no `qa_*` tables, no `qa_team` built-in role. The only shared
> infrastructure available to QA reviewers today is the Files study browser + viewer
> (read-only) and audit logs.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: study browsing + viewer for QA review (`/`, `/files/:id`) — no QA-specific FR is fully implemented | (viewer ACs) | S |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R05-01 | **QA Review Queue** — filterable, paginated queue | No `/api/v2/qa/queue` endpoint; no `qa_queue` table | AC-R05-01..10 | L |
| FR-R05-02 | **QA Review Workflow** (pass/fail, dose entry, sequence checklist) | No `/api/v2/qa/review/{study_uid}` endpoints | AC-R05-11..20 | M |
| FR-R05-03 | **Protocol Registry CRUD** | No `/api/v2/qa/protocols` endpoints; no `protocols` table | AC-R05-21..33 | M |
| FR-R05-04 | **QA Score Persistence** (`qa_scores` write) | No `qa_scores` table; no QA form | AC-R05-34..43 | M |
| FR-R05-05 | **Corrective Action Inbox** | No `/api/v2/qa/corrective-actions` endpoints | AC-R05-44..54 | M |
| FR-R05-06 | **Incident/Retake Logging** | No `/api/v2/qa/incidents` endpoints; no `incidents` table | AC-R05-55..64 | M |
| FR-R05-07 | **RBAC QA Role** (`qa_team` built-in, `QA_READ`/`QA_WRITE`/`PROTOCOL_MANAGE`) | `QA_*` permissions not in `permissions.py` | AC-R05-65..71 | S |
| FR-R05-08 | **Automated Dose Validation** (DRL flags on ingestion) | No rules engine; no dose baseline data | AC-R05-72..79 | L |
| FR-R05-10 | **Peer Review Workflow** (assign to R12, discrepancy analysis) | No peer-review endpoints; depends on R12 reporting | AC-R05-151 | L |
| FR-R05-11 | **ACR Phantom QA** (scheduled phantom scans, auto-analysis) | No phantom scheduling; v3.1 scope | AC-R05-152 | L |
| FR-R05-12 | **Regulatory Reporting** (MQSA/ACR/state exports) | No reporting engine; v3.1 scope | AC-R05-152 | L |
| FR-R05-13 | **AI-assisted QA** (artifact detection) | No AI integration; v3.2 scope | — (no AC yet) | L |
| NFR-R05-01..10 | QA queue/form/incident performance, WCAG, pagination | Blocked on FR-R05-01..06 above | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Backend QA module (queue/review/protocols/incidents/corrective-actions endpoints + 5 tables) | FR-R05-01..07 | AC-R05-01..71 | Entire QA package; must be raised with backend before sprint commitment |
| R12 structured reporting | FR-R05-10 | AC-R05-151 | Peer review depends on original report availability |
| `QA_READ`/`QA_WRITE`/`PROTOCOL_MANAGE` permission slugs | FR-R05-07 | AC-R05-65..71 | RBAC role cannot ship without permissions |

## Next Steps (highest priority)

1. **Raise QA module with backend** — queue/review/protocol/incident/corrective-action endpoints + schema; unblocks FR-R05-01..07; L effort
2. **Add `QA_*` permission slugs + `qa_team` built-in role** — unblocks FR-R05-07; S effort
3. **Update roadmap each sprint** as FR/NFR status changes
