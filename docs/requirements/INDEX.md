# Requirements Packages Index

All requirements packages organized by role. Each package follows the
[pacs-requirements-architect skill](../../.opencode/skills/pacs-requirements-architect/SKILL.md)
conventions.

| Role | ID | Slug | Version | Artifacts | Traceability | Roadmap | Status |
|------|----|------|---------|-----------|--------------|---------|--------|
| Super Admin (PACS Admin) | R01 | super-admin | 1.2.1 | 8 | ✓ | ✓ | approved |
| Hospital IT / Tenant Admin | R02 | tenant-admin | 1.2.2 | 8 | ✓ | ✓ | draft |
| Radiology & Imaging Service Director | R03 | service-director | 1.2.1 | 8 | ✓ | ✓ | approved |
| Radiology & Service Coordinator | R04 | service-coordinator | 1.2.0 | 8 | ✓ | ✓ | draft |
| Radiology Services QI/QA Team | R05 | qa-team | 1.3.0 | 8 | ✓ | ✓ | approved |
| Radiology Technologist | R06 | technologist | 1.2.0 | 8 | ✓ | ✓ | approved |
| Radiology Technician | R07 | technician | 1.2.0 | 8 | ✓ | ✓ | approved |
| Front Desk (Receptionist) | R08 | front-desk | 1.1.2 | 8 | ✓ | ✓ | draft |
| Radiology Service Cashier | R09 | cashier | 1.1.2 | 8 | ✓ | ✓ | draft |
| Biomedical Engineer | R10 | biomedical-engineer | 1.1.2 | 8 | ✓ | ✓ | draft |
| Radiology Service Nursing Team | R11 | nursing | 1.1.2 | 8 | ✓ | ✓ | draft |
| Staff Radiologist | R12 | staff-radiologist | 1.3.0 | 8 | ✓ | ✓ | approved |
| Radiology Trainee/Resident | R13 | resident | 1.2.0 | 8 | ✓ | ✓ | draft |
| Referring Clinician | R14 | referring-clinician | 1.2.1 | 8 | ✓ | ✓ | approved |
| External RIS | R15 | external-ris | 1.1.1 | 8 | ✓ | ✓ | draft |
| External EMR | R16 | external-emr | 1.1.1 | 8 | ✓ | ✓ | draft |
| External PACS | R17 | external-pacs | 1.1.1 | 8 | ✓ | ✓ | draft |
| Teleradiologist | R18 | teleradiologist | 1.3.0 | 8 | ✓ | ✓ | approved |
| Other Hospital Staff | R19 | hospital-staff | 1.1.2 | 8 | ✓ | ✓ | draft |

All packages re-verified 2026-08-03 against the post-merge codebase (merge
`4d136e0`: R04 schedule board, R05 QI/QA module, R06/R07 exam lifecycle,
R12/R13/R18 reading, reporting, peer review and reading presets). Each package
contains a `DELTA.md` documenting the changes and a `feedback.md` for the
stakeholder review loop; see per-role `CHANGELOG.md`.

## Cross-Role Dependencies

- **R01 → R02**: Super Admin provisions tenants; Tenant Admin operates within them
- **R01 → R15/R16/R17**: Super Admin configures external integrations (HL7, FHIR, DICOM)
- **R03/R05 → R01**: Service Director and QI/QA consume infrastructure metrics from Super Admin
- **R12/R18 → R01**: Radiologists depend on storage/replica health and routing rules configured by Super Admin

## Package Status Legend

| Status | Meaning |
|--------|---------|
| approved | Package has passed all validation gates and is ready for sprint planning |
| draft | Package is being refined; not yet ready for implementation planning |
| gated | Some requirements are blocked on backend/frontend work |
| not started | No requirements package exists yet |