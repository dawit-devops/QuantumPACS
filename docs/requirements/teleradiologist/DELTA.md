# Delta — Teleradiologist (R18) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped reading/reporting/peer-review/presets
- **Version change**: 1.2.0 → 1.3.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements

| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R18-01 | Status (GATED → Partial); Notes | See W1 workflow | Reading worklist shipped (`GET /reports/reading-list`, priority-sorted); site filter + assignment filter GATED | R12 reading worklist shipped; telerad filters missing |
| FR-R18-03 | Status (GATED → Implemented); Notes | v3.0 OAuth per PRD-v3.md U-v3.5 | `/oauth/login`, `/oauth/callback`, `/oauth/token`, `/oauth/providers`, OIDC discovery + tenant switcher (`TenantSelector.tsx`, `/tenants*`) | SSO/OIDC + tenant switching shipped |
| FR-R18-04 | Status (GATED → Implemented); Notes | Feature parity: MPR, MIP, 3D, hanging protocols | Same viewer as R12 (`frontend/src/detail/*`, DICOMweb QIDO/WADO) | Viewer parity by shared surface |
| FR-R18-05 | Status (GATED → Implemented); Notes | Performance target for remote reading | Capability shipped; WAN-budget (10 Mbps) verification pending | DICOMweb viewer shipped |
| FR-R18-07 | Status (GATED → Implemented); Notes | Distinct from final reports | Draft → preliminary → final state machine + preliminary flow in `ReportEditor.tsx` | Preliminary reporting shipped |
| FR-R18-08 | Status (GATED → Implemented); Notes | Workflow flexibility for credentialed readers | `POST /reports/{exam_id}/sign` (REPORT_SIGN) finalizes; per-site credential check not enforced | Sign-off shipped |
| FR-R18-22 | Status (GATED → Partial); Notes | Home office ergonomics | Layout presets (1x1/1x2/2x2) per modality via `/reading-presets`; 3-monitor profiles GATED | Layout presets shipped |
| FR-R18-24 | Status (GATED → Partial); Notes | Reading efficiency | W/L + layout presets per modality shipped (`STANDARD_WL` Brain/Stroke/Bone/Lung/Mediastinum); scenario template set GATED | Preset stack approximates hanging protocols |
| FR-R18-02, 06, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23 | Status (unchanged GATED) | GATED | GATED | No offline/escalation/consult/dashboard/dictation/mobile/prefetch/messaging endpoints exist |

## Impact on Existing Artifacts

| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01-user-requirements.md | Yes | Notes updated for FR-R18-01/03/04/05/07/08/22/24; Codebase Status, API Dependency Analysis (existing vs flagged), feasibility note rewritten |
| 02-workflow-maps.md | No | Unchanged (workflows still aspirational for telerad-specific flows) |
| 03-user-stories.md | No | Stories cover gated workflows; reporting/SSO slices now backed by shipped endpoints |
| 06-acceptance-criteria.md | Yes | AC group headers annotated PARTIAL/GATED per current codebase; peer-review out-of-scope note updated; Overall Verdict + Next Steps rewritten |
| 07-traceability.md | Yes | FR/NFR → AC table corrected to Covered with real AC IDs; GATED section rewritten per-FR with blocking deps |
| 08-implementation-roadmap.md | Yes | Implemented/Partial/Missing sections restructured with real endpoints; blocking deps + next steps updated |
| README.md | Yes | Codebase Alignment rewritten with real routes/pages/permissions; version 1.3.0; API lists + open questions updated |
| CHANGELOG.md | Yes | [1.3.0] entry added |
