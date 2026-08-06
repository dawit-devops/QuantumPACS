# PACS — UI/UX Requirements

**Document:** 04 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Requirements apply to the **zero-footprint web viewer** (OHIF/Cornerstone-class), the **reading worklist**, the **PACS admin console**, and **tenant/ops dashboards**. IDs: `PAC-UI-…`. Priorities: M/D/O. Baseline references: `docs/specs/worklist_design.md`, `research/pacs-ris-viewer-integration-spec.md` (§5).

---

## 1. Cross-Cutting UX Principles (all personas)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-01 | **Speed is a feature:** first-frame render < 3 s on reference bandwidth; no full-study download before display (progressive/partial retrieval). | M |
| PAC-UI-02 | **Consistency:** shared design tokens, keyboard shortcuts, and iconography across viewer, worklist, and admin consoles (see `docs/design-tokens.json`). | M |
| PAC-UI-03 | **Keyboard-first for clinical power users:** every common action (scroll, zoom, window/level, layout, next study, dictation toggle) has a documented shortcut; shortcuts configurable per user. | M |
| PAC-UI-04 | **Session resilience:** in-progress work (worklist filters, open studies, WIP reports) restored on re-login/reconnect. | D |
| PAC-UI-05 | **Accessibility:** WCAG 2.1 AA — keyboard navigability, focus states, screen-reader labels, contrast ≥ 4.5:1 for text; colorblind-safe overlays (never color-only warnings). | M |
| PAC-UI-06 | **Localization:** time zones per site; date/number formats configurable; bilingual (e.g., EN/AR per tenant) for clinical text where tenant requires. | D |
| PAC-UI-07 | **Audit visibility:** users see a "who accessed/exported" trail for studies where policy requires (patient-facing reassurance, HIPAA). | O |

## 2. Reading Worklist (Radiologist · Technologist)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-08 | Worklist rows show: priority/STAT badge, patient name/ID (masked per policy), age/sex, modality, body part, requested procedure, accession, study date, status, priors indicator, AI-flag indicator. | M |
| PAC-UI-09 | Default sort by priority (STAT > inpatient > outpatient), then study date; persisted per user; filters: modality, site, date range, status, unread-only toggle. | M |
| PAC-UI-10 | Search by patient ID/name, accession, MRN; server-side with pagination (`total` returned, not client-side count — per `worklist_design.md`). | M |
| PAC-UI-11 | Batch actions: assign to radiologist, mark read, route, export. Status guard: only valid transitions enabled (e.g., "Mark Performed" only for scheduled entries). | M |
| PAC-UI-12 | Table + calendar views; row click opens study in viewer; double-click opens in new tab for side-by-side comparisons. | D |
| PAC-UI-13 | Critical-finding studies show persistent alert badge until acknowledged; acknowledged time recorded. | M |

## 3. Diagnostic Viewer (Radiologist · Teleradiologist)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-14 | **Hanging protocols:** automatic layout selection (1×1, 2×2, 3×3, 2×4, mixed), per user/per anatomy, one-click override, saved on change. | M |
| PAC-UI-15 | **Priors panel:** side-by-side current vs. prior with synchronized scrolling option; thumbnails of all priors with modality/anatomy labels; one-click swap. | M |
| PAC-UI-16 | **Toolbar (context-sensitive):** window/level presets (e.g., brain, lung, mediastinum, abdomen), zoom, pan, measure (length, angle, ROI, ellipse, line profile), annotate, cine (speed control), MPR, MIP/MinIP, 3D, fusion toggle, invert, flip/rotate, reset. | M |
| PAC-UI-17 | **Key image bookmarking:** single-click star per instance/frame; bookmarks appear as thumbnails and auto-link into report template. | D |
| PAC-UI-18 | **AI overlay:** flags rendered as overlay icons with confidence %; toggle accept/reject; rejected AI findings do not render. | O |
| PAC-UI-19 | **Study/series navigator:** thumbnail strip with series labels (series number, description, images, dose info); click to load; show series with no images (warnings). | M |
| PAC-UI-20 | **Loading states:** skeleton/progressive bar for first frames; explicit error + retry for failed series; never a blank viewport. | M |
| PAC-UI-21 | **Multi-monitor:** workspaces span multiple displays (configurable per user); window-level layout persisted. | D |
| PAC-UI-22 | **Measurements & annotations persist** with the study (DICOM SR / GSPS) and are visible to co-readers per policy. | D |

## 4. Acquisition / QC UI (Technologist)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-23 | Upload/ingest status panel: per-series progress, success/failure, duplicate detection ("already stored — duplicate"), retry button. Per `docs/specs/uploads_design.md`. | M |
| PAC-UI-24 | QC review screen: open acquired series, mark Adequate/Inadequate with mandatory reject reason code, send to correct accession. | D |
| PAC-UI-25 | Clear visual confirmation of Storage Commitment (green check "Archived — safe to purge") at the console-facing UI. | M |

## 5. PACS Admin Console (Admin · Informatics)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-26 | Modality registry table: AE title, IP/host, tenant, make/model, status (online/offline/last seen), enable/disable, edit. | M |
| PAC-UI-27 | Routing rules builder: source modality/site → target archive/viewer/queue; rule precedence visible; dry-run validation. | D |
| PAC-UI-28 | Queue monitor: DICOM queue depth, stuck-message detection, per-interface error counts, one-click retry/drain. | M |
| PAC-UI-29 | Storage dashboard: per-tenant usage vs. quota with color bar (green <50%, orange 50–75%, red >75% — per `tenants_design.md`), tier breakdown, growth trend, alert threshold config. | M |
| PAC-UI-30 | Retention policy editor: per-document-type clocks (5–30+ yr, pediatric), legal-hold toggles with reason + audit, dry-run of what would be purged. | M |
| PAC-UI-31 | Exception/orphan worklist: failed studies with reason, patient/accession mismatch highlight, merge/reassign actions. | M |
| PAC-UI-32 | Audit log viewer: structured columns (time, actor, event, resource, tenant), filters by event type/date/actor/tenant, CSV export, cursor pagination — per `audit-logs_design.md`. | M |
| PAC-UI-33 | Migration tool UI: source inventory, progress %, count reconciliation report, sample-validation task list. | D |

## 6. Tenant & Ops Dashboards (Tenant Admin · Super Admin)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-34 | Usage metering dashboard: studies stored, WADO bytes/egress, MWL queries, API calls by tenant/period; export to CSV. | M |
| PAC-UI-35 | Invoice/billing view: plan, base amount, overage lines (egress/storage), period, status; drill to usage detail. Per `pacs-ris-multitenancy.md` §7. | M |
| PAC-UI-36 | Tenant card grid: name, domain, status badge (active/pending/quarantined/decommissioned), storage bar, user/study counts, actions — per `tenants_design.md`. | M |
| PAC-UI-37 | Provisioning progress: skeleton/spinner with stage (QUEUED→…→READY) visible; actions disabled until READY. | M |
| PAC-UI-38 | KPI dashboards (TAT, retrieval, backlog, utilization): time-series charts, drill-down to outliers, scheduled export. | D |

## 7. Viewer Launch UX (Referring MD · ED MD)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-39 | One-click launch from EMR (SMART on FHIR) that lands directly on the correct study (no search). | D |
| PAC-UI-40 | Simplified read-only mode for referring physicians: report + key images + basic tools; no dictation/editing controls. | M |
| PAC-UI-41 | Share-link view (`/view/:key`) renders read-only with friendly expired/invalid message (per `share_design.md`, `auth_design.md`). | D |

## 8. Mobile/Responsive (Referring MD · ED MD)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| PAC-UI-42 | Responsive viewer for tablets/phones: touch gestures (pinch zoom, swipe series), portrait/landscape, limited-but-useful toolset. | D |
| PAC-UI-43 | Offline/shared-device caution: no PHI cached on device; session timeouts; screen lock on blur. | M |

## Acceptance linkage

Every `PAC-UI-*` above is testable via the corresponding persona acceptance criteria in `06_acceptance_criteria.md` (e.g., PAC-UI-08…13 → PAC-AC-P01-01; PAC-UI-14…22 → PAC-AC-P01-02/04/10).
