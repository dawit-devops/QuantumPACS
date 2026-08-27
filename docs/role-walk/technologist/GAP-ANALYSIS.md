# technologist — Gap Analysis (Phase 2)
Date: 2026-08-28
Sources: ADR-017, PRD-v3, iam-audit.md, permissions.py, api/exams.py

## Gaps

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| G1 | Patient/study writes | ADR-017 §Role table: "files/patients/studies: read + write" | PATIENT_READ only (no PATIENT_WRITE, STUDY_WRITE) | LOW | permissions.py:376-392 | Docs drift: R2-14 intentionally removed PATIENT_WRITE/STUDY_WRITE from Matrix A rows. The technologist creates/changes patients via front-desk workflows, not the exam console. |
| G2 | Critical-results flagging | ADR-017 does not mention CRITICAL_RESULTS_WRITE for technologist | Technologist holds CRITICAL_RESULTS_WRITE | LOW | permissions.py:387 | The technologist may flag a critical finding during QA (exam console Flag Critical button). This is reasonable — the exam is in the acquisition phase and the technologist observes a finding. |
| G3 | PHI audit — exam console | ADR-017 §Audit: every PHI access must be logged | Exam console logs events (exam.images_opened, exam.qa_completed, etc.) | PASS | api/exams.py:270-691 | Multiple audit events fire during the exam lifecycle. Verify clinical-scoped events fire for the technologist's tenant. |
| G4 | Tenant scoping — clinical data-plane | ADR-016 + ADR-029: tenant-bound data-plane | Exams/worklist queries include tenant filter | PASS | db/exams.py, db/worklist.py | Clinical endpoints query with tenant_id. Verify in backend walk. |
| G5 | DICOMWEB_READ legacy grant | ADR-017: technologist can upload (FILE_WRITE) | DICOMWEB_READ is granted (legacy) | LOW | permissions.py:377 | Technologist doesn't see the DICOMweb admin console (clinical-scoped). The grant is for STOW uploads. Consistent with the DICOMweb surface. |

## Skills invoked
hipaa-compliance (G3 — PHI audit), pacs-workflow (G6 — exam workflow).