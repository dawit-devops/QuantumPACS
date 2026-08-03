# Feedback — External RIS (R15)

Stakeholder review loop for the External RIS requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | RIS integration lead (vendor) |
| **Package** | `docs/requirements/external-ris/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh external-ris` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R15-01 | 08-implementation-roadmap.md | `FR-R15-03` remains GATED. Outbound exam status (HL7 ORM/ORU), report delivery, reconciliation — GATED; inbound HL7/MWL/MPPS-style status via /exams partial. | open |
| OQ-R15-02 | 08-implementation-roadmap.md | `FR-R15-04` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R15-03 | 08-implementation-roadmap.md | `FR-R15-07` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R15-01 | | | | open | | |
| FB-R15-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
