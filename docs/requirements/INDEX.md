# Requirements Packages Index

All requirements packages organized by role. Each package follows the
[pacs-requirements-architect skill](../../.opencode/skills/pacs-requirements-architect/SKILL.md)
conventions.

| Role | ID | Slug | Artifacts | Traceability | Roadmap | Status |
|------|----|------|-----------|--------------|---------|--------|
| Super Admin (PACS Admin) | R01 | super-admin | 8 | ✓ | ✓ | approved |
| Hospital IT / Tenant Admin | R02 | tenant-admin | 8 | ✓ | ✓ | draft |
| Radiology & Imaging Service Director | R03 | service-director | 8 | ✓ | ✓ | approved |
| Radiology & Service Coordinator | R04 | service-coordinator | 8 | ✓ | ✓ | draft |
| Radiology Services QI/QA Team | R05 | qa-team | 8 | ✓ | ✓ | approved |
| Radiology Technologist | R06 | technologist | 8 | ✓ | ✓ | draft |
| Radiology Technician | R07 | technician | 8 | ✓ | ✓ | draft |
| Front Desk (Receptionist) | R08 | front-desk | 8 | ✓ | ✓ | draft |
| Radiology Service Cashier | R09 | cashier | 8 | ✓ | ✓ | draft |
| Biomedical Engineer | R10 | biomedical-engineer | 8 | ✓ | ✓ | draft |
| Radiology Service Nursing Team | R11 | nursing | 8 | ✓ | ✓ | draft |
| Staff Radiologist | R12 | staff-radiologist | 8 | ✓ | ✓ | draft |
| Radiology Trainee/Resident | R13 | resident | 8 | ✓ | ✓ | draft |
| Referring Clinician | R14 | referring-clinician | 8 | ✓ | ✓ | approved |
| External RIS | R15 | external-ris | 8 | ✓ | ✓ | draft |
| External EMR | R16 | external-emr | 8 | ✓ | ✓ | draft |
| External PACS | R17 | external-pacs | 8 | ✓ | ✓ | draft |
| Teleradiologist | R18 | teleradiologist | 8 | ✓ | ✓ | draft |
| Other Hospital Staff | R19 | hospital-staff | 8 | ✓ | ✓ | draft |

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