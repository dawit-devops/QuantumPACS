# technologist — Recommendations (Phase 3)
Date: 2026-08-28
Reference: iam-audit (least privilege), multi-tenant-saas (tenant isolation), hipaa-compliance

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 docs drift | Docs are the contract (ADR-017 §Role table says "read + write" for patients/studies) | UPDATE-DOCS: ADR-017/PRD-v3 technologist row → "files/studies: read + write; patients: read" (R2-14 intentionally removed PATIENT_WRITE/STUDY_WRITE) | S | LOW | **DEFER** (2026-08-28) — open docs item, priority LOW |
| R2 | G2 CRITICAL_RESULTS_WRITE | Least privilege — a grant must be exercised | KEEP (no change): the exam console Flag Critical action exercises the grant; the upsert is audited (exam.critical_flagged). Document the surface in the user guide. | S | LOW | **KEEP** (2026-08-28) — no change; document in Phase 6 guide |
| R3 | G5 DICOMWEB_READ legacy | Least privilege | KEEP (no change): used by STOW uploads; console hidden (clinical-scoped). No action. | S | LOW | **DEFER** (2026-08-28) — revisit if STOW path changes; priority LOW |

## Skills invoked
iam-audit (least privilege), multi-tenant-saas (tenant isolation), hipaa-compliance (audit).