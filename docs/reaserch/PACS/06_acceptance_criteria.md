# PACS — Acceptance Criteria

**Document:** 06 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Testable acceptance criteria per user story (`03_user_stories.md`) and per feature area. Used as UAT scripts and automated test assertions. Each block lists **Given / When / Then** scenarios and the story it verifies.

---

## PAC-P01 · Radiologist

### PAC-AC-P01-01 — Prioritized reading worklist (→ PAC-US-P01-01)
- **GIVEN** a worklist with STAT, inpatient, and outpatient studies **WHEN** the radiologist opens it **THEN** STAT studies sort first, then inpatient, then outpatient, by study date desc.
- **GIVEN** modality/site/date-range filters **WHEN** applied **THEN** only matching studies are shown and the filter set persists across sessions.
- **GIVEN** pagination **WHEN** the list is longer than one page **THEN** the total count comes from the server and page navigation is accurate.
- **GIVEN** an entry not yet scheduled **WHEN** the user attempts "Mark Performed" **THEN** the action is disabled with an explanatory tooltip.

### PAC-AC-P01-02 — Hanging protocols (→ PAC-US-P01-02)
- **GIVEN** a CT chest study **WHEN** opened **THEN** the default CT-chest hanging protocol (e.g., 2×4 layout, lung + mediastinum windows) is applied automatically.
- **GIVEN** a user-defined layout override **WHEN** the radiologist saves it **THEN** the protocol is persisted and applied on subsequent opens for that user/anatomy.
- **GIVEN** an unrecognized anatomy/modality **WHEN** a study opens **THEN** a sensible generic protocol is applied and the user is prompted to save a preference.

### PAC-AC-P01-03 — Priors prefetch & one-click comparison (→ PAC-US-P01-03)
- **GIVEN** a scheduled exam **WHEN** it becomes eligible for prefetch **THEN** prior studies are staged to the reading-site edge cache before read time (≥ 95% availability at read; SLA PAC-SL-24).
- **GIVEN** a study with priors **WHEN** the radiologist clicks "Priors" **THEN** prior thumbnails list within 3 s and open side-by-side with synchronized scroll.
- **GIVEN** priors residing under another facility in the same health system **WHEN** accessed **THEN** access is policy-gated, authorized in < 1 s, and logged to audit with the acting tenant context.
- **GIVEN** no priors exist **WHEN** the panel is opened **THEN** an explicit "No prior studies found" message is shown (no empty/blank state).

### PAC-AC-P01-04 — Diagnostic tools (→ PAC-US-P01-04)
- **GIVEN** any CT/MR study **WHEN** the radiologist uses the toolbar **THEN** window/level presets, zoom, pan, cine (with speed), MPR, MIP/MinIP, 3D (CT), PET/CT fusion (PET pairs), and measurement tools render correctly and interactively.
- **GIVEN** measurements **WHEN** drawn **THEN** numeric results display accurately and export to the report where configured.

### PAC-AC-P01-05 — AI results in viewer (→ PAC-US-P01-05)
- **GIVEN** an AI result exists for a study **WHEN** the study is opened **THEN** the flag/overlay renders with confidence value and an accept/reject control.
- **GIVEN** an AI finding is rejected **WHEN** the radiologist saves **THEN** the finding no longer renders and the rejection is audited.
- **GIVEN** no AI results **WHEN** the study opens **THEN** no AI UI is shown (clean viewer).

### PAC-AC-P01-06 — Critical results flagging (→ PAC-US-P01-06)
- **GIVEN** a study with an urgent finding **WHEN** the radiologist flags "Critical" **THEN** a documented notification (message/call task) is created for the responsible physician with timestamp.
- **GIVEN** the notification **WHEN** the physician acknowledges **THEN** acknowledgment time is recorded and the worklist badge clears; unacknowledged alerts escalate after configured timeout.
- **GIVEN** the flag **WHEN** the report is signed **THEN** the critical flag is embedded in the ORU/FHIR DiagnosticReport payload.

### PAC-AC-P01-07 — Key images linked to report (→ PAC-US-P01-07)
- **GIVEN** a bookmarked key image **WHEN** the radiologist signs the report **THEN** the key image thumbnail/URL is included in the report and viewable by the referring physician.

### PAC-AC-P01-08 — Study open < 3 s (→ PAC-US-P01-08)
- **GIVEN** an active study on a diagnostic workstation **WHEN** selected **THEN** first frames render in < 3 s (p95) on reference hardware/bandwidth.
- **GIVEN** a large (multi-GB) study **WHEN** opened in the web viewer **THEN** the first frames appear progressively in < 3 s without waiting for full download (PAC-AC-P01-10 covers detail).

### PAC-AC-P01-09 — WIP preservation (→ PAC-US-P01-09)
- **GIVEN** an unfinished read (open study, drafted report) **WHEN** the radiologist logs out/in or switches device **THEN** the WIP state is restored (study open, report draft intact, no duplicate report created).

### PAC-AC-P01-10 — Large-study progressive rendering (→ PAC-US-P01-10)
- **GIVEN** a 2+ GB CT study over reference bandwidth **WHEN** opened **THEN** frames stream progressively (frame-level WADO-RS), first frames < 3 s, and the viewer never becomes unresponsive.
- **GIVEN** a series fails to load **WHEN** the failure occurs **THEN** an explicit error with Retry is shown and the rest of the study remains usable.

## PAC-P02 · Technologist

### PAC-AC-P02-01 — MWL auto-population (→ PAC-US-P02-01)
- **GIVEN** a scheduled order **WHEN** the modality queries the worklist **THEN** patient name/ID, accession, requested procedure, and body part return and auto-fill the console without manual entry.
- **GIVEN** a worklist query with no matching entries **WHEN** executed **THEN** an empty result with a clear message is returned (no misleading default data).

### PAC-AC-P02-02 — Storage Commitment (→ PAC-US-P02-02)
- **GIVEN** a completed C-STORE **WHEN** the study passes validation and is archived **THEN** Storage Commitment success is returned to the modality and shown in the console UI before any cache purge prompt.
- **GIVEN** a failed store **WHEN** the modality requests commitment **THEN** a failure response is returned; the UI shows failure with retry and the scanner cache is NOT purged.

### PAC-AC-P02-03 — Send feedback & retry (→ PAC-US-P02-03)
- **GIVEN** a DICOM send **WHEN** it fails **THEN** the failure appears in the upload status panel with reason and a one-click retry; success shows a green confirmation.
- **GIVEN** a duplicate upload **WHEN** sent **THEN** the response is `200 {duplicate: true}` with the existing record id (per `uploads_design.md`) and a "duplicate" label.

### PAC-AC-P02-04 — MPPS flow (→ PAC-US-P02-04)
- **GIVEN** a modality starts a procedure **WHEN** it sends MPPS IN PROGRESS **THEN** the tracking board shows In Progress; COMPLETED updates to Completed; DISCONTINUED shows Discontinued with reason — all without manual entry.
- **GIVEN** an MPPS mismatch (wrong accession) **WHEN** received **THEN** it is routed to the exception worklist, not silently dropped.

### PAC-AC-P02-05 — Redo/add series (→ PAC-US-P02-05)
- **GIVEN** a repeated or added series **WHEN** sent with the same accession **THEN** it appends to the correct study and is retrievable as part of it.

### PAC-AC-P02-06 — QC review (→ PAC-US-P02-06)
- **GIVEN** an acquired series **WHEN** the technologist marks it Inadequate **THEN** a reject reason is mandatory, the series is flagged, and the redo flow is offered.

### PAC-AC-P02-07 — Specialty workflows (→ PAC-US-P02-07)
- **GIVEN** an ultrasound exam **WHEN** sent **THEN** cine loops and measurements archive completely.
- **GIVEN** a mammography exam **WHEN** sent **THEN** tomosynthesis series and MQSA QC records are preserved and retrievable.

## PAC-P03 · Teleradiologist

### PAC-AC-P03-01 — Tokenized multi-facility session (→ PAC-US-P03-01)
- **GIVEN** a teleradiologist with an OAuth2 session **WHEN** they access facilities granted by contract **THEN** they read studies from all granted tenants without per-facility logins or VPN; every access is audit-logged with facility context.
- **GIVEN** an unauthorized facility **WHEN** access is attempted **THEN** it is denied with an audited access-denied event.

### PAC-AC-P03-02 — Progressive streaming (→ PAC-US-P03-02)
- **GIVEN** a 500 MB study on a 25 Mbps link **WHEN** opened **THEN** first frames render < 5 s (SLA PAC-SL-12) and the read proceeds while later frames stream.

### PAC-AC-P03-03 — Cross-facility priors (→ PAC-US-P03-03)
- **GIVEN** a patient with priors at another client facility **WHEN** the teleradiologist requests them **THEN** they are served under the audited cross-tenant policy and appear in the priors panel.

### PAC-AC-P03-04 — Critical callback (→ PAC-US-P03-04)
- **GIVEN** a critical finding during a remote read **WHEN** flagged **THEN** on-site staff at the ordering facility are notified and acknowledgment is tracked; unacknowledged escalates.

### PAC-AC-P03-05 — Report routing (→ PAC-US-P03-05)
- **GIVEN** a signed remote report **WHEN** finalized **THEN** it routes to the correct ordering facility's RIS/EMR via ORU/FHIR and appears in that tenant's records only.

## PAC-P04 · PACS Administrator

### PAC-AC-P04-01 — Modality registration & security (→ PAC-US-P04-01)
- **GIVEN** a new modality **WHEN** registered **THEN** it requires AE title + IP allow-list scoped to a tenant; unregistered AE titles are rejected and logged.
- **GIVEN** an IP change on a registered modality **WHEN** updated **THEN** the change is audited and immediately effective.

### PAC-AC-P04-02 — Routing rules (→ PAC-US-P04-02)
- **GIVEN** routing rules by modality/site/anatomy **WHEN** a study matches **THEN** it routes to the correct destination; precedence is deterministic; a queue monitor shows depth and stuck messages with one-click retry.

### PAC-AC-P04-03 — Retention & legal hold (→ PAC-US-P04-03)
- **GIVEN** retention clocks configured per document type (5–30+ yr, pediatric) **WHEN** age thresholds pass **THEN** only compliant purges occur; legal-hold overrides block purges and are audited; 0 accidental purges (PAC-SL-43).

### PAC-AC-P04-04 — Storage quota visibility (→ PAC-US-P04-04)
- **GIVEN** storage usage near quota **WHEN** it crosses 75%/90% **THEN** tenant admin is alerted; the dashboard shows usage vs. quota with color coding; optional hard-stop blocks new ingestion.

### PAC-AC-P04-05 — Exception worklist (→ PAC-US-P04-05)
- **GIVEN** a study failing validation (no accession / mismatched patient) **WHEN** received **THEN** it appears in the exception worklist with reason; reconciliation actions (merge, assign accession, discard with audit) are available; 100% of orphans resolved within 24 h (PAC-SL-22).

### PAC-AC-P04-06 — Audited export (→ PAC-US-P04-06)
- **GIVEN** an export request **WHEN** executed **THEN** format selection (DICOM/PDF/CD/DVD/XDS-I.b), anonymization toggle, and reason code are captured; the export is logged with actor/time/study/recipient.

### PAC-AC-P04-07 — DR failover (→ PAC-US-P04-07)
- **GIVEN** a cloud-region outage **WHEN** failover triggers **THEN** active reads continue from edge cache; ingestion buffers; full restore meets RTO ≤ 4 h and RPO ≤ 60 min (PAC-SL-03/04); a quarterly DR drill produces documented evidence.

### PAC-AC-P04-08 — Interface health dashboard (→ PAC-US-P04-08)
- **GIVEN** an interface failure (DICOM queue backlog, HL7 drop, modality offline) **WHEN** it occurs **THEN** an alert fires within 5 min and the dashboard shows the fault with drill-down; > 99.9% message delivery baseline (PAC-SL-23).

### PAC-AC-P04-09 — Migration reconciliation (→ PAC-US-P04-09)
- **GIVEN** a legacy migration **WHEN** complete **THEN** study/series/instance counts reconcile 100% against source; a random sample (1–2%) validates clinically; report available.

## PAC-P05 · Informatics · PAC-P06/07 · Referring/ED · PAC-P08 · Manager · PAC-P19/20 · Admins

### PAC-AC-P05-01 — KPI dashboards (→ PAC-US-P05-01)
- **GIVEN** the KPI dashboard **WHEN** opened **THEN** retrieval time, TAT by priority, backlog, and modality utilization render with drill-down to individual studies; data refreshes within 5 min of source changes.

### PAC-AC-P05-02 — Hanging protocol library (→ PAC-US-P05-02)
- **GIVEN** a protocol library version **WHEN** published **THEN** it applies to target sites/specialties; changes are versioned and rollback is one click.

### PAC-AC-P06-01 — EMR one-click launch (→ PAC-US-P06-01)
- **GIVEN** an EMR with SMART on FHIR **WHEN** the physician clicks the study **THEN** the viewer launches in-context (correct patient/study), first frame < 5 s (PAC-SL-13), token refresh transparent, and no PHI appears in URLs.

### PAC-AC-P06-02 — Automatic report delivery (→ PAC-US-P06-02)
- **GIVEN** a signed report **WHEN** finalized **THEN** it is delivered to the EMR via ORU/FHIR DiagnosticReport without manual forwarding and is visible in the patient chart.

### PAC-AC-P06-03 — Responsive viewing (→ PAC-US-P06-03)
- **GIVEN** a clinic tablet/phone **WHEN** the physician opens the viewer **THEN** layout adapts, touch gestures work, and no PHI is cached on the device.

### PAC-AC-P07-01 — STAT prioritization (→ PAC-US-P07-01)
- **GIVEN** a STAT order **WHEN** it enters the pipeline **THEN** it is prioritized in acquisition and reading queues above routine work; status visible to ED.

### PAC-AC-P07-02 — Preliminary read visibility (→ PAC-US-P07-02)
- **GIVEN** a preliminary/critical read **WHEN** available **THEN** the ED physician sees it immediately with a link to contact the radiologist; acknowledgment is tracked.

### PAC-AC-P08-01 — Manager dashboards & export (→ PAC-US-P08-01)
- **GIVEN** the manager dashboard **WHEN** a report period is selected **THEN** TAT/utilization/backlog aggregate correctly and export to CSV matches on-screen data.

### PAC-AC-P19-01 — Tenant storage visibility (→ PAC-US-P19-01)
- **GIVEN** the tenant admin dashboard **WHEN** opened **THEN** usage vs. quota, tier breakdown, and growth trend are shown; export matches metering data.

### PAC-AC-P19-02 — Role-based user management (→ PAC-US-P19-02)
- **GIVEN** a tenant admin **WHEN** they add/remove users or change roles **THEN** changes take effect immediately (token version bump on permission change), are audit-logged, and re-login reflects new permissions.

### PAC-AC-P20-01 — Atomic tenant provisioning (→ PAC-US-P20-01)
- **GIVEN** a new tenant signup **WHEN** provisioning runs **THEN** it completes atomically (facility + TRIAL subscription + seed data + RLS scope) and reports READY < 15 min; any failure rolls back with no partial tenant (per `provision_tenant()`).

### PAC-AC-P20-02 — Usage metering & invoicing (→ PAC-US-P20-02)
- **GIVEN** metered events (studies stored, WADO bytes, API calls) **WHEN** a billing period closes **THEN** the invoice line items match metered usage exactly (PAC-SL-50) and are visible to the tenant.

### PAC-AC-P20-03 — Audited cross-tenant access (→ PAC-US-P20-03)
- **GIVEN** a cross-tenant read (priors/teleradiology) **WHEN** performed **THEN** it requires an explicit policy grant; the event is audit-logged with source & target facility; an attempted unauthorized cross-tenant read is denied and logged.

---

## Traceability matrix

| Story group | Acceptance | Notes |
| :--- | :--- | :--- |
| PAC-US-P01-01…10 | PAC-AC-P01-01…10 | Radiologist reading path |
| PAC-US-P02-01…07 | PAC-AC-P02-01…07 | Acquisition path |
| PAC-US-P03-01…05 | PAC-AC-P03-01…05 | Remote reading |
| PAC-US-P04-01…09 | PAC-AC-P04-01…09 | Administration |
| PAC-US-P05/06/07/08/19/20 | PAC-AC-P05…P20 | Informatics, referring, ED, ops |
