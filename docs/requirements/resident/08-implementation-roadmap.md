# Implementation Roadmap — Radiology Trainee/Resident (R13)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 10 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | 5 workflows |
| 03 | User Stories | `03-user-stories.md` | done | 10 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | Supervised viewer, editor, dashboards |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 10 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 20 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 20 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared R12 stack (merge 4d136e0)**: reading worklist (`/reports/reading-list`), draft report editor + autosave (`GET/PUT /reports/{exam_id}`), report templates (`/reports/templates`), peer review (`/peer-reviews*`), reading presets (`/reading-presets*`), notifications (`exam.completed` + `/ws`) — no resident-specific FR is fully implemented | (viewer/reading ACs) | S |
| NFR-R13-02 | Draft report auto-save latency ≤ 300ms — autosave loop shipped in shared `ReportEditor.tsx` | AC-R13-12 | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R13-01 | Supervised worklist — shared reading worklist exists (`/reports/reading-list`); attending-assignment column, WebSocket auto-refresh, supervision status do not | Requires attending-assignment data + supervised-status columns | AC-R13-01 | M |
| FR-R13-02 | Supervised viewer — shared viewer exists; attending-guidance panel + guidance channel do not | No guidance channel | AC-R13-02 | M |
| FR-R13-03 | Draft report editor — draft creation + autosave shipped via shared R12 reporting; "Awaiting Attending Review" badge, completeness/word-count indicator, submit-to-attending do not | Attending-review workflow (FR-R13-04) | AC-R13-03 | M |
| FR-R13-04 | Attending review/co-sign — `/peer-reviews*` covers review of final signed reports only; no resident-draft side-by-side review, approve/co-sign, or return-for-revision | No resident-draft co-sign workflow | AC-R13-04 | L |
| FR-R13-06 | Exam list — study/patient list infra exists (Files browser); exam-log filters, CSV export, metrics do not | No resident exam-log view/endpoints | AC-R13-06 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R13-05 | Teaching file capture | No de-identification service | AC-R13-05 | L |
| FR-R13-07 | Feedback dashboard | No resident metrics aggregates | AC-R13-07 | M |
| FR-R13-08 | On-call consult | No consult/notification routing | AC-R13-08 | M |
| FR-R13-09 | Protocol learning | No education-annotation store | AC-R13-09 | M |
| FR-R13-10 | Case conference export | Depends on teaching files + presentation export | AC-R13-10 | M |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single endpoint or UI component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; requires backend + frontend coordination |
| L (Large) | 11+ | Cross-cutting feature; requires integration contract or new infrastructure |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; exam-list infrastructure identified as existing.

### Phase 2: Unblock GATED requirements (next priority)
1. **Attending-assignment data + supervised worklist columns** — required for FR-R13-01 / AC-R13-01
   - Owner: Backend; Blocks: AC-R13-01; Effort: M
   - Shared reading worklist (`/reports/reading-list`) is the base to extend.
   - Once done, re-run validator gate on AC-R13-01.
2. **Attending-guidance channel** — required for FR-R13-02 / AC-R13-02
   - Owner: Backend; Blocks: AC-R13-02; Effort: M

### Phase 3: Attending-review workflow + resident features (shared R12 reporting exists)
3. **Draft submit/approve/return + attending review queue** — FR-R13-03 (submit slice), FR-R13-04; build on shipped `GET/PUT /reports/{exam_id}` (L)
4. **Teaching file capture + de-identification** — FR-R13-05; L
5. **Exam-log filters, CSV export, metrics** — FR-R13-06; M
6. **Feedback dashboard aggregates** — FR-R13-07; M
7. **On-call consult routing** — FR-R13-08; M
8. **Protocol learning store** — FR-R13-09; M
9. **Case conference export** — FR-R13-10; M

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Resident-draft attending-review workflow (submit/approve/return queue) | FR-R13-03, 04 | AC-R13-03, 04 | No draft co-sign/supervision workflow (shared draft editor + peer review shipped) |
| Attending-assignment data | FR-R13-01 | AC-R13-01 | No supervised worklist columns |
| Guidance channel | FR-R13-02 | AC-R13-02 | No attending guidance in viewer |
| Resident exam-log view/endpoints | FR-R13-06 | AC-R13-06 | Exam list has no resident-specific filters/export/metrics |
| De-identification service | FR-R13-05, 10 | AC-R13-05, 10 | Teaching files can't publish |
| Consult routing | FR-R13-08 | AC-R13-08 | On-call guidance unavailable |

## Next Steps (highest priority)

1. **Attending review/co-sign workflow (submit/approve/return)** — unblocks AC-R13-03/04; L effort (shared draft editor is the foundation)
2. **Attending-assignment data + supervised worklist columns** — unblocks AC-R13-01; M effort
3. **Attending-guidance channel** — unblocks AC-R13-02; M effort
4. Update this roadmap each sprint as FR/NFR status changes.
