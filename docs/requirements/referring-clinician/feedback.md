# Feedback — Referring Clinician (R14)

Stakeholder review loop for the Referring Clinician requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | Chief of clinical services (referring MD) |
| **Package** | `docs/requirements/referring-clinician/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh referring-clinician` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R14-01 | 08-implementation-roadmap.md | `FR-R14-04` remains GATED. Clinician portal, report retrieval (REPORT_READ-gated), follow-up requests, mobile viewer — GATED; SSO admin scaffolding partial. | open |
| OQ-R14-02 | 08-implementation-roadmap.md | `FR-R14-05` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-03 | 08-implementation-roadmap.md | `FR-R14-06` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-04 | 08-implementation-roadmap.md | `FR-R14-07` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-05 | 08-implementation-roadmap.md | `FR-R14-08` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-06 | 08-implementation-roadmap.md | `FR-R14-09` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-07 | 08-implementation-roadmap.md | `FR-R14-10` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-08 | 08-implementation-roadmap.md | `FR-R14-11` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R14-09 | 08-implementation-roadmap.md | `FR-R14-12` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R14-01 | | | | open | | |
| FB-R14-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
