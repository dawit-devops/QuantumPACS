# Feedback — Other Hospital Staff (R19)

Stakeholder review loop for the Other Hospital Staff requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | Nursing/lab/pharmacy representative |
| **Package** | `docs/requirements/hospital-staff/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh hospital-staff` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R19-01 | 08-implementation-roadmap.md | `FR-R19-01` remains GATED. Portal shell, order awareness, notifications, scope model — GATED; viewer/file access shared infra exists. | open |
| OQ-R19-02 | 08-implementation-roadmap.md | `FR-R19-03` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R19-03 | 08-implementation-roadmap.md | `FR-R19-04` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R19-04 | 08-implementation-roadmap.md | `FR-R19-06` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R19-05 | 08-implementation-roadmap.md | `FR-R19-07` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R19-06 | 08-implementation-roadmap.md | `FR-R19-08` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R19-07 | 08-implementation-roadmap.md | `FR-R19-10` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R19-01 | | | | open | | |
| FB-R19-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
