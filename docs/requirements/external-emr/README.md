# Requirements Package — R16 External EMR

| Field | Value |
|-------|-------|
| **Version** | 1.1.1 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified 2026-08-03 post-merge 4d136e0)

**Interface surface**: API-only (no web UI). See artifact 04 — "System Interface
Surface": HL7 ADT receiver, FHIR Patient read/search, ImagingStudy +
DocumentReference scaffolding, webhook delivery all exist.

**Implemented**: HL7 ADT inbound, FHIR Patient read/search, webhook push.
**GATED**: report backfill job, results-status workflow, async demographics sync with
conflict resolution — flagged to backend.

**Post-merge re-verification (4d136e0)**: no new EMR-facing surface. FHIR
Patient/ImagingStudy/DocumentReference routes and HL7 ADT receiver unchanged; exam
status now exists internally (`/exams/{id}/complete` → worklist `performed`) but is
**not** exposed to the EMR as FHIR resource status or ORU — FR-R16-05 (results
status) remains GATED. Report backfill (FR-R16-04) still blocked on R12 reporting
delivery.

## Role Summary

**Persona**: External Electronic Medical Record system exchanging patient
demographics, order context, and reports with QuantumPACS. System-to-system
(no end-user UI).
**Access tier**: Integration — HL7 ADT (MLLP), FHIR R4 (HTTPS).
**Context**: The operational surface is the existing FHIR admin + HL7 admin
screens used by R01/R02.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R08 Front Desk** — registration triggers ADT; inbound ADT upserts patients.
- **R11 Nursing** — allergy/pregnancy flags via ADT for safety screening.
- **R12/R18 Radiologist** — finalized reports delivered as DiagnosticReport/ORU.
- **R01/R02 Admin** — FHIR/HL7 config, clients, monitoring.
- **R15 External RIS / R17 External PACS** — shared patient/order/image identities.

## Flagged Gaps (backend — must be raised before sprint commitment)

- Report → DiagnosticReport mapping not confirmed (blocked on R12 reporting).
- Demographics outbound (PACS → EMR) not wired.
- Allergy/pregnancy flag extraction to R11 not verified end-to-end.
- FHIR client scope enforcement (SMART-on-FHIR backend services) needs audit.
