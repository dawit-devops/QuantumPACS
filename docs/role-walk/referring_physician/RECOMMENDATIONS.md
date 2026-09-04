# referring_physician — Recommendations (Phase 3)
Date: 2026-08-29
Reference: iam-audit (least privilege), hipaa-compliance
Skills invoked: iam-audit

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 — ADR-017 "files: read" imprecise | Docs are the contract | **UPDATE-DOCS**: change ADR-017 referring_physician row from "files/patients/studies: read" to "patients/studies/viewer: read; files (via viewer grants)" — the actual grant opens Files via STUDY_READ/VIEWER_READ, not FILE_READ | S | LOW | UPDATE-DOCS (approved) |

## Decisions applied
- **R1** (UPDATE-DOCS): ADR-017 referring_physician row corrected.