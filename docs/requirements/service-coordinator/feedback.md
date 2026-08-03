# Feedback — Radiology & Service Coordinator (R04)

Stakeholder review loop for the Radiology & Service Coordinator requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | Chief radiology technologist / scheduler |
| **Package** | `docs/requirements/service-coordinator/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh service-coordinator` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R04-01 | 08-implementation-roadmap.md | `FR-R04-02` remains GATED. Schedule board shipped (FR-R04-01/06/10); assignment, drag-move persistence, utilization, staffing, conflicts, handoff GATED on a /schedule backend. | open |
| OQ-R04-02 | 08-implementation-roadmap.md | `FR-R04-03` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R04-03 | 08-implementation-roadmap.md | `FR-R04-04` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R04-04 | 08-implementation-roadmap.md | `FR-R04-05` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R04-05 | 08-implementation-roadmap.md | `FR-R04-07` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R04-06 | 08-implementation-roadmap.md | `FR-R04-08` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R04-07 | 08-implementation-roadmap.md | `FR-R04-09` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R04-01 | | | | open | | |
| FB-R04-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
