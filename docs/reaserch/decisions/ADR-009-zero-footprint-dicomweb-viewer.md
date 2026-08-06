# ADR-009: Zero-Footprint DICOMweb Viewer with Progressive Streaming

## Status
Accepted

## Date
2026-08-04

## Context
Radiologists must read on diagnostic workstations and anywhere (teleradiology, referring-MD launch from EMR) without installing software. Studies can exceed 2 GB (CT) — the viewer must render first frames in < 3 s (PAC-SL-11) without waiting for full download, keep priors/context available, and never block on a failed series. The viewer is the product surface most visible to the primary persona (radiologist).

## Decision
Build the viewer as a **zero-footprint web application consuming only DICOMweb** (QIDO-RS/WADO-RS/frame-level WADO-RS per ADR-003):

- **Rendering:** progressive/frame-level streaming — first frames < 3 s p95, explicit error + Retry on failed series, never a blank viewport (PAC-AC-P01-08/10, PAC-UI-20).
- **Reading worklist:** prioritized (STAT > inpatient > outpatient, study date desc), server-side pagination (`total` from server), persisted filters, batch actions with status guards (PAC-AC-P01-01; per `docs/specs/worklist_design.md`).
- **Hanging protocols:** automatic layout selection (1×1…3×3, 2×4, mixed) by anatomy/modality with per-user overrides persisted (PAC-AC-P01-02, PAC-UI-14).
- **MVP toolset:** window/level presets, zoom/pan, measure, annotate, cine, reset — the diagnostic baseline; MPR/MIP/3D/fusion deferred to v1.1 (PAC-AC-P01-04).
- **Diagnostic support:** critical-flag → notification + acknowledgment tracking (PAC-AC-P01-06); key-image bookmarks bound into the report (PAC-AC-P01-07); WIP preservation across sessions (PAC-AC-P01-09).
- **Auth & distribution:** IUA/OAuth2 token gate, UID-based links, no PHI in URLs (ADR-004); SMART-on-FHIR in-context launch is the v2.0 referring-MD surface (PAC-AC-P06-01).
- **AI overlays** (accept/reject with confidence) are v1.1 (PAC-AC-P01-05) — the rendering architecture (overlay layers) must anticipate them without shipping them in MVP.

## Alternatives Considered

### Thick diagnostic workstation only (vendor install)
- Pros: maximal tools (MPR/3D), calibrated display control
- Cons: install + update burden per seat; no teleradiology; no EMR launch
- Rejected as sole surface: the platform needs anywhere-access; workstations remain an integration (DICOM/DICOMweb) but not the viewer strategy

### Build viewer on DIMSE pull (C-MOVE to client)
- Pros: uses legacy protocol
- Cons: no progressive web streaming, firewall-hostile, per-facility client config
- Rejected: DICOMweb is the web-native retrieval path (ADR-003)

### Render-all-then-display (download whole study first)
- Pros: simpler state model
- Cons: multi-GB studies stall reading; fails the < 3 s first-frame SLA outright
- Rejected: frame-level progressive streaming is non-negotiable (PAC-AC-P01-10)

## Consequences
- The < 3 s first-frame and never-blank guarantees become gate G3 acceptance criteria with explicit perf tests (T-SL-10/11/16/17).
- The viewer is FE-heavy: two dedicated viewer engineers in Sprint 4; hanging-protocol fallback to a generic protocol for unknown anatomies is required (PAC-AC-P01-02).
- Rendering layer is built overlay-ready so AI results (v1.1) and fusion (v1.1) plug in without rework.
- The same viewer shell is the base for the EMR SMART-on-FHIR launch surface (v2.0) — shared-platform reuse per the consolidated roadmap §3.

## Sources
`research/pacs-ris-viewer-integration-spec.md` §4–§6 (QIDO/WADO/frame-level, IUA) · `docs/specs/worklist_design.md` · `requrements/PACS/06_acceptance_criteria.md` PAC-AC-P01-01/02/06/07/08/09/10 · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-10/11/16/17 · sprint4 (E-PAC-06) · `requrements/qa_test_strategy.md` §3.1
