# Feedback — Radiology Services QI/QA Team (R05)

Stakeholder review loop for the Radiology Services QI/QA Team requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | QA/QC program lead |
| **Package** | `docs/requirements/qa-team/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh qa-team` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R05-01 | 08-implementation-roadmap.md | `FR-R05-08` remains GATED. Automated dose validation, DICOM tag validation, ACR phantom QA, regulatory reporting, AI QA — all GATED on rules engine; confirm v3.1 scope. | open |
| OQ-R05-02 | 08-implementation-roadmap.md | `FR-R05-09` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R05-03 | 08-implementation-roadmap.md | `FR-R05-11` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R05-04 | 08-implementation-roadmap.md | `FR-R05-12` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R05-05 | 08-implementation-roadmap.md | `FR-R05-13` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R05-01 | | | | open | | |
| FB-R05-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
