# radiologist — Gap Analysis (Phase 2)

Date: 2026-08-27
Docs reviewed: ADR-017 (RBAC model), docs/iam-audit.md (2026-08-12), RBAC matrix spec,
docs/PRD-v3.md, docs/requirements/service-director/
Code reviewed: `backend/api/permissions.py`, `backend/api/reports.py`, `backend/api/reading_presets.py`

## Findings

| # | Surface | Documented (ADR/audit/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| R1 | Permission docs | ADR-017: radiologist has `files/patients/studies: read + write; logs: read` | Code grants `FILE_READ`, `PATIENT_READ`, `STUDY_READ` (no write); no `LOG_READ` or `AUDIT_READ` | MEDIUM | `ADR-017.md:74` vs `permissions.py:402-412` | ADR table is stale/overbroad — update to match `MATRIX_A_RAD_TEL` |
| R2 | REPORT_TEMPLATE_ADMIN | RBAC spec Matrix A: ✓ for RAD/TEL | `REPORT_TEMPLATE_ADMIN` is in `MATRIX_A_RAD_TEL` (permissions.py:216) but **never enforced** — all template endpoints gate on `REPORT_WRITE` | LOW | `permissions.py:107,216` — grep `@requires_permission.*REPORT_TEMPLATE_ADMIN` = 0 hits | Dead permission: granted but unused |
| R3 | PHI read audit | HIPAA §164.312(b) audit controls: "Who accessed what PHI, when" | Report/reading GET handlers (reading list, report open, imaging tree, prior reports, peer review open) do NOT write audit log events. Only state transitions (save/sign/submit/return) are audited. | MEDIUM | `reports.py` — all GET handlers lack `AuditLog` calls | PHI reads are invisible — no audit trail for which radiologist viewed which patient |
| R4 | IAM authn | iam-audit H-1/H-2: no MFA, localStorage token | Still open — highest blast radius for clinical roles (PHI session theft) | HIGH | `auth.py`, `session.ts` | H-1, H-2 per super_admin G3; applies equally to radiologist |
| R5 | IAM tenant | M-4: `hf` tenant missing DB → 500 | Teleradiologist with `CROSS_TENANT_READ` hits 500 when `hf` tenant DB is missing (dev only) | MEDIUM | Tenant registry, `hf` DB doesn't exist | Dev env only; prod configures per-tenant DB correctly |
| R6 | DICOMWEB_READ | Radiologist in Matrix A: NOT listed; Matrix C: SYSTEM_ADMIN/TENANT_ADMIN only | `DICOMWEB_READ` carried via `LEGACY_RADIOLOGIST` union, retained in migration 062 | LOW | `permissions.py:45,383`; `RBAC_matrix_spec.md:230` | Legacy-but-intentional; not documented anywhere except enum comment |
| R7 | Auditor docs drift | ADR-017: `auditor` removed (G2 resolved) | `PRD-v3.md` lines 127,412 + service-director reqs still reference `auditor` role | LOW | `PRD-v3.md:127,412` | Stale references from prior PRD version |
| R8 | Tenant scoping | ADR-029: per-tenant DB pools | Report/reading handlers rely on tenant pool (`get_conn()`); no explicit tenant_id checks in handlers. Correct for per-tenant DB architecture. | PASS | All report handlers | No explicit tenant check needed when DB is per-tenant |

Severity: CRITICAL > HIGH > MEDIUM > LOW > PASS.

## Key observations

- **R1 + R2**: The ADR-017 table is inaccurate for the radiologist role — it claims write access to files/patients/studies and log access, none of which the code grants. The canonical source is `MATRIX_A_RAD_TEL` from the RBAC matrix spec.
- **R3 (PHI read audit)**: This is the most significant radiologist-specific finding. HIPAA requires audit controls for PHI access. Currently, only write/state-change operations are logged. Every time a radiologist opens a report or views images, this is invisible to the audit trail.
- **R4**: Same G3 findings from super_admin walk — no MFA, localStorage token — apply equally to all clinical roles handling PHI, making the blast radius even larger.
- **R6**: DICOMWEB_READ is legacy but deliberately retained. Radiologist cannot use the DICOMweb admin console (`adminOnly`), but can access DICOMweb QIDO/WADO-RS endpoints programmatically. This is intentional.

## Open from prior audit (applies to radiologist)

- H-1 No MFA, H-2 localStorage access token, M-5 token in login body, M-3 query-string token fallback.