# radiologist — Best-Practice Recommendations (Phase 3)

Date: 2026-08-27
Skills referenced: iam-audit (audit controls, application authorization), hipaa-compliance
(§164.312(b) audit controls, §164.308 minimum necessary)

## Recommendations

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | ADR-017 radiologist row overbroad (files/patients/studies read+write, logs:read) | iam-audit: role definitions match code | Docs: update ADR-017 table to reflect `MATRIX_A_RAD_TEL` (read-only files/patients/studies, no logs) | Small | MEDIUM | DEFER (2026-08-27) |
| R2 | `REPORT_TEMPLATE_ADMIN` granted but never enforced (template endpoints gate `REPORT_WRITE`) | iam-audit: permission checks centralized; granted permissions must be enforced | Backend: add `@requires_permission(Permission.REPORT_TEMPLATE_ADMIN)` to template create/publish/rollback | Small | LOW | ENFORCE (2026-08-27) |
| R3 | PHI read operations (report open, images, priors, peer-review open) not audited | HIPAA §164.312(b): audit controls for PHI access; who accessed what/when | Backend: add `AuditLog` events to report/reading GET handlers | Medium | MEDIUM | ADD-AUDIT (2026-08-27) |
| R4 | No MFA, localStorage token (H-1/H-2) | HIPAA §164.312(d) person/entity authentication | Dedicated IAM-hardening sprint (same as super_admin G3) | Large | HIGH | DEFER-to-sprint |
| R5 | `hf` tenant missing DB in dev → teleradiologist cross-tenant 500 | — | Dev: create + migrate `hf` DB so CROSS_TENANT_READ doesn't 500 | Small | MEDIUM | FIXED-DEV-DB (2026-08-27) — created `hf` DB + alembic upgrade head (122 tables); notify listener now connects |
| R6 | `DICOMWEB_READ` legacy-but-retained undocumented | — | Docs: note legacy status in RBAC matrix spec / ADR | Small | LOW | PENDING |
| R7 | `auditor` role stale refs in PRD-v3 + service-director docs | iam-audit: docs drift | Docs: drop `auditor` from PRD-v3.md + requirements | Small | LOW | DEFER (2026-08-27) |
| R8 | Tenant scoping | ADR-029 per-tenant DB pools | Verified correct — no handler-level tenant check needed | — | — | PASS |

## Open items requiring user decision

1. **R6**: Document DICOMWEB_READ legacy status in the RBAC matrix spec (or ADR-017).
