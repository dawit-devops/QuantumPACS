# Feedback — Radiology Service Cashier (R09)

Stakeholder review loop for the Radiology Service Cashier requirements package.
Package version: see [README.md](README.md). Review target: all artifacts
(`01`–`08`) with focus on the open questions below.

## Primary Stakeholder

| Field | Value |
|-------|-------|
| **Role** | Billing office lead |
| **Package** | `docs/requirements/cashier/` |
| **Review due** | 2026-08-10 (1 week after post-merge alignment) |
| **Gate** | Package stays `approved`/`draft` per review outcome; each item below must resolve to `resolved` or `deferred` with rationale |

## How to Submit Feedback

For each item, record: artifact + section affected (e.g., `08-implementation-roadmap.md`, "Phase 2"),
the feedback, and a proposed disposition. The requirements architect then updates the relevant
artifact(s), re-runs the quality gates (`scripts/validate-requirements.sh cashier` + Sections 6.1–6.4
of the skill), and moves the item to `resolved` or `deferred` with rationale.

## Open Questions (seeded from post-merge alignment, 2026-08-03)

| ID | Affects | Question | Status |
|----|---------|----------|--------|
| OQ-R09-01 | 08-implementation-roadmap.md | `FR-R09-01` remains GATED. Billing data model + endpoints do not exist; cashier role has PATIENT_READ/WRITE only. Confirm billing is out of scope for v3.1. | open |
| OQ-R09-02 | 08-implementation-roadmap.md | `FR-R09-02` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-03 | 08-implementation-roadmap.md | `FR-R09-03` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-04 | 08-implementation-roadmap.md | `FR-R09-04` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-05 | 08-implementation-roadmap.md | `FR-R09-05` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-06 | 08-implementation-roadmap.md | `FR-R09-06` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-07 | 08-implementation-roadmap.md | `FR-R09-07` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-08 | 08-implementation-roadmap.md | `FR-R09-08` remains GATED. Confirm priority / v3.1 scope. | open |
| OQ-R09-09 | 08-implementation-roadmap.md | `FR-R09-10` remains GATED. Confirm priority / v3.1 scope. | open |

## Feedback Items

| FB ID | Artifact / Section | Feedback | Proposed Disposition | Status | Owner | Date |
|-------|--------------------|----------|----------------------|--------|-------|------|
| FB-R09-01 | | | | open | | |
| FB-R09-02 | | | | open | | |

## Status Legend

| Status | Meaning |
|--------|---------|
| open | Awaiting stakeholder input |
| acknowledged | Stakeholder reviewed; architect processing |
| resolved | Artifacts updated; validation gates re-run |
| deferred | Deferred with documented rationale (recorded in DELTA.md) |
