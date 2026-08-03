# Delta — Radiology Technician (R07) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped the shared exam lifecycle (backend `api/exams.py` + frontend `frontend/src/technologist/`) covering FR-R07-01..08
- **Version change**: 1.1.0 → 1.2.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R07-01 | Status | GATED | Implemented | `TechnologistWorklist.tsx` at `/exams`; data via `GET /worklist?modality=` (shared lifecycle, no dedicated technician UI) |
| FR-R07-02 | Status | GATED | Implemented | `POST /exams/{id}/identity-confirm` (spec name `confirm-patient`) |
| FR-R07-03 | Status | GATED | Implemented | `GET /exams/{id}/protocol`, `GET /protocols?modality=` |
| FR-R07-04 | Status | GATED | Implemented | `POST /exams/{id}/acquisitions`, `POST /exams/{id}/acquisitions/{aid}/{decision}` (accept/reject/retake) — covers DR/CR |
| FR-R07-05 | Status | GATED | Implemented | `GET/POST /exams/{id}/dose` (DLP, CTDIvol) |
| FR-R07-06 | Status | GATED | Implemented | `POST /exams/{id}/safety-checks`; `safety_checks` table |
| FR-R07-07 | Status | GATED | Implemented | `POST /exams/{id}/complete`; LISTEN/NOTIFY status push |
| FR-R07-08 | Status | GATED | Implemented | `GET/POST /exams/{id}/incidents`; `incidents` table |
| FR-R07-09 | Status | GATED | GATED (unchanged) | No `dap` column in `acquisitions`; no `/fluoroscopy-start`, `/spot-capture`, `/cine-start`, `/cine-stop` endpoints |
| FR-R07-10 | Status | GATED | GATED (unchanged) | No `agd` column in `acquisitions`; no mammo-specific endpoints; tomosynthesis v3.1 |
| FR-R07-11..13 | Status | GATED (v3.1) | GATED (unchanged) | No AI integration (v3.2), no dose-baseline job, no HL7 ORM integration |

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01 User Requirements | Yes | Codebase Status rewritten: FR-R07-01..08 implemented via shared lifecycle; FR-R07-09/10 GATED with schema/endpoint blockers |
| 04 UI/UX Requirements | Yes | Route table: `/exams` + `/exams/:id` accessible (`EXAM_READ`); fluoro/mammo flows GATED |
| 06 Acceptance Criteria | Yes | Implementation status note added; AC-R07-01..08 verifiable; AC-R07-09/10 remain GATED |
| 07 Traceability | Yes | GATED section replaced with per-FR Implementation Status + endpoint mapping |
| 08 Roadmap | Yes | Implemented (Passing ACs) table; phases 1–3 implemented, phase 4 (fluoro/mammo) GATED; shipped API names corrected; blocking deps narrowed |
| README | Yes | Codebase Alignment rewritten; endpoint/permission/schema sections annotated shipped (`acquisitions` table; `dap`/`agd` NOT shipped) |
| CHANGELOG | Yes | 1.2.0 entry added |
