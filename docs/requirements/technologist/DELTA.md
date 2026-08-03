# Delta — Radiology Technologist (R06) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped the R06 exam lifecycle end-to-end (backend `api/exams.py` + frontend `frontend/src/technologist/`)
- **Version change**: 1.1.0 → 1.2.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R06-01 | Status | GATED | Implemented | `TechnologistWorklist.tsx` at `/exams`; 30s auto-refresh; data via `GET /worklist?modality=` |
| FR-R06-02 | Status | GATED | Implemented | `POST /exams/{id}/identity-confirm` (spec name `confirm-patient`) |
| FR-R06-03 | Status | GATED | Implemented | `GET /exams/{id}/protocol`, `GET /protocols?modality=`; ExamConsole protocol panel |
| FR-R06-04 | Status | GATED | Implemented | `POST /exams/{id}/acquisitions`, `POST /exams/{id}/acquisitions/{aid}/{decision}` (accept/reject/retake) |
| FR-R06-05 | Status | GATED | Implemented | `GET/POST /exams/{id}/dose` (DLP, CTDIvol) |
| FR-R06-06 | Status | GATED | Implemented | `POST /exams/{id}/safety-checks`; `safety_checks` table |
| FR-R06-07 | Status | GATED | Implemented | `POST /exams/{id}/complete`; LISTEN/NOTIFY status push |
| FR-R06-08 | Status | GATED | Implemented | `GET/POST /exams/{id}/incidents`; `incidents` table |
| FR-R06-09 | Status | GATED | Implemented | `POST /exams/{id}/overrides`; `protocol_overrides` table |
| FR-R06-10 | Status | GATED | Implemented | `MODALITY_WORKFLOWS` in ExamConsole (CT/MR/PET/US) + modality protocol presets |
| FR-R06-11..13 | Status | GATED (v3.1) | GATED (unchanged) | No AI integration (v3.2), no dose-baseline job, no HL7 ORM integration |

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01 User Requirements | Yes | Codebase Status rewritten: exam lifecycle implemented with endpoints/role; GATED remainder listed |
| 04 UI/UX Requirements | Yes | Route table: `/exams` + `/exams/:id` accessible (`EXAM_READ`); gating split implemented vs GATED |
| 06 Acceptance Criteria | Yes | Implementation status note added; ACs verifiable via backend tests + E2E + visual evidence |
| 07 Traceability | Yes | GATED section replaced with per-FR Implementation Status + endpoint mapping |
| 08 Roadmap | Yes | Implemented (Passing ACs) table; phases marked implemented; shipped API names corrected; blocking deps narrowed |
| README | Yes | Codebase Alignment rewritten; endpoint/permission/schema sections annotated shipped (`acquisitions` table) |
| CHANGELOG | Yes | 1.2.0 entry added |
