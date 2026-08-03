# Backend Requirements — Index

## Overview

QuantumPACS uses a persona-based requirements model. Each document describes what the frontend displays, what actions it performs, what states it handles, and what data it expects from the backend — organized per feature area. This index maps every requirements document to the personas it serves and provides a quick reference for backend developers.

### Personas

| # | Persona | Description |
|---|---------|-------------|
| P1 | **Radiologist** | Diagnostic user — views studies, annotates, shares with referring physicians |
| P2 | **Technologist** | Uploads DICOM files, manages worklist, verifies studies |
| P3 | **Clinician** | Referring/reviewing physician — views shared studies, limited interaction |
| P4 | **PACS Admin** | System configuration — users, roles, tenants, routing, audit, metrics |
| P5 | **Modalities** | Automated DICOM devices (CT, MR, XA) pushing/pulling studies via C-STORE, C-FIND |
| P6 | **RIS** | External Radiology Information System exchanging orders and results |
| P7 | **EMR** | External Electronic Medical Record system reading patient/imaging data |
| P8 | **Front Desk** | Registration/scheduling receptionist — patient search, order intake, check-in, consent |
| P9 | **Cashier** | Radiology billing/payments — invoices, receipts, claims, reconciliation (read-only clinical context) |
| P10 | **Biomedical Engineer** | Equipment registry, PM/QC, downtime, tickets, vendor contracts (no PHI) |
| P11 | **Nursing Team** | Bedside patient care — prep, vitals, contrast, adverse reactions, MAR, recovery |
| P12 | **Other Hospital Staff** | Limited read-only imaging/results portal for non-radiology staff (ward-scoped) |

## Persona → Feature Mapping

| Feature Area | File | P1 Rad | P2 Tech | P3 Clin | P4 Admin | P5 Modal | P6 RIS | P7 EMR |
|---|---|---|---|---|---|---|---|---|
| Auth | `auth/` | X | X | X | X | X | X | X |
| Study List | `study-list/` | X | X | X | X | | | |
| Search | `search/` | X | X | X | X | | | |
| Viewer | `viewer/` | X | X | X | | | | |
| Worklist | `worklist/` | | X | | X | X | | |
| Uploads | `uploads/` | | X | | X | | | |
| Share | `share/` | X | | X | | | | |
| Account | `account/` | X | X | X | X | | | |
| Patient Page | `patient-page/` | X | X | X | | | | |
| Notifications | `notifications/` | X | X | X | X | | | |
| Metrics | `metrics/` | | X | | X | | | |
| Users | `users/` | | | | X | | | |
| Roles | `roles/` | | | | X | | | |
| Tenants | `tenants/` | | | | X | | | |
| Replicas | `replicas/` | | | | X | | | |
| Routing Rules | `routing-rules/` | | X | | X | | | |
| Audit Logs | `audit-logs/` | | | | X | | | |
| Service Keys | `service-keys/` | | X | | X | X | X | X |
| DICOM MWL SCP | `dicom-mwl-scp/` | | X | | X | X | | |
| DICOMweb | `dicomweb/` | | | | | X | | X |
| FHIR R4 API | `fhir-r4-api/` | | | | X | | | X |
| HL7 ADT/ORM | `hl7-adt-orm/` | | | | X | | X | X |
| HL7 Integration | `hl7-integration/` | | | | X | | X | X |
| Phase 4 Integration | `phase4-integration/` | | | | X | | X | X |
| Existing Screens | `existing-screens/` | X | X | X | X | | | |

## Feature Documents

### Core User Features

| # | Directory | Covers | Primary Personas | Status |
|---|-----------|--------|-----------------|--------|
| 1 | `auth/` | Login (password + SSO), session management, token refresh, share-key access, API key auth, lockout logic | All P1–P7 | **Final** |
| 2 | `study-list/` | Search results table, global search bar, column filters, advanced search modal (12 DICOM fields), upload modal, bulk download, pagination, mobile cards, URL-encoded bookmarkable state | P1, P2, P3, P4 | **Draft** |
| 3 | `search/` | Three search modes (global, column, advanced), ES primary + QIDO-RS fallback, special character handling, sort/pagination, tenant-scoped search | P1, P2, P3, P4 | **Draft** |
| 4 | `viewer/` | Cornerstone3D DICOM viewer, toolset (pan/zoom/WWWL/annotations), multi-instance navigation, data tab (metadata), audit trail, share tab, measurement panel, WebSocket annotation sync | P1, P2, P3 | **Draft** |
| 5 | `worklist/` | MWL entry table/calendar, CRUD for scheduled procedures, status transitions (scheduled→performed→cancelled), auto-transition on C-STORE, filter by station/status, C-FIND MWL query support | P2, P4, P5 | **Draft** |
| 6 | `uploads/` | Multipart DICOM upload, SHA-256 hashing, patient/study/series hierarchy creation, storage backend copy, per-file progress, cancel, retry, drag-and-drop | P2, P4 | **Draft** |
| 7 | `share/` | Expiring share links, share-key creation/deletion, view-only access (no annotations/download), key validation, read-only viewer mode | P1, P3 | **Draft** |
| 8 | `account/` | User profile view/edit, change password, active sessions list (future), logout-all (future) | All P1–P4 | **Draft** |
| 9 | `patient-page/` | Patient demographics display, study hierarchy tree, HL7 sync source badge | P1, P2, P3 | **Draft** |
| 10 | `notifications/` | In-app notification bell + list, real-time WebSocket delivery (Redis pub/sub), per-user event type preferences, read/unread state, retentio, badge counts on nav | P1, P2, P3, P4 | **Planned** |

### Admin Features

| # | Directory | Covers | Primary Personas | Status |
|---|-----------|--------|-----------------|--------|
| 11 | `metrics/` | Stat cards (patients/studies/series/files/users/storage), system health panel, modality distribution chart, component latency, ingestion trend, latest files, time range selector, auto-refresh | P4, P2 | **Draft** |
| 12 | `users/` | User list table, inline role change, password reset, create/deactivate user, bulk CSV import, role permission tooltip | P4 | **Draft** |
| 13 | `roles/` | RBAC role list, 34 permission slugs across 13 domains, CRUD roles, built-in role protection (5 roles), role simulation/test, role→user assignment listing | P4 | **Draft** |
| 14 | `tenants/` | Tenant card grid, provisioning flow (DB creation + schema migration + role seeding), status lifecycle (provisioning→active→quarantined→decommissioned), storage quota tracking, custom domain | P4 | **Draft** |
| 15 | `replicas/` | Storage replica management (local/S3/B2), master replica designation, sync delay/progress tracking, health checks, failover trigger, repair/delete operations | P4 | **Draft** |
| 16 | `routing-rules/` | DICOM auto-routing rules with condition trees (eq/ne/contains/gt/gte/lt/lte/$or), priority ordering, test endpoint, match counting, all-matching-rules-applied semantics | P4, P2 | **Draft** |
| 17 | `audit-logs/` | HIPAA-compliant event log table, 30+ event types (data access, auth, config changes, DICOM, system), expandable JSON payload rows, tenant-scoped + cross-tenant views, CSV export | P4 | **Draft** |
| 18 | `service-keys/` | API key management (qpk_ prefix), SHA-256 hashed storage, read/revoke/create, permission scoping, last-used tracking | P4, P2, P5, P6, P7 | **Draft** |

### Integration Features

| # | Directory | Covers | Primary Personas | Status |
|---|-----------|--------|-----------------|--------|
| 19 | `dicom-mwl-scp/` | DICOM C-FIND MWL SCP implementation, worklist entry CRUD via UI, modality AET management, query logging, auto-populate study UID on C-STORE match | P2, P4, P5 | **Draft** |
| 20 | `dicomweb/` | DICOMweb QIDO-RS / WADO-RS / STOW-RS endpoints, capability discovery, fallback support | P5, P7 | **Planned** |
| 21 | `fhir-r4-api/` | FHIR R4 Patient, ImagingStudy, DocumentReference resources, CapabilityStatement, SMART-on-FHIR backend services, admin config/monitoring | P4, P7 | **Draft** |
| 22 | `hl7-adt-orm/` | HL7 v2.x MLLP listener, ADT (A01/A08/A03/A04/A05) handlers for patient upsert, ORM (O01) handler for worklist creation, message dashboard, error stats | P4, P6, P7 | **Draft** |
| 23 | `hl7-integration/` | HL7 integration overview, connection management, message flow architecture | P4, P6, P7 | **Planned** |
| 24 | `phase4-integration/` | Combines F4.1–F4.3 (HL7 + FHIR + Routing): scope breakdown, sprint plan, risks, and cross-feature dependencies | P4, P6, P7 | **Draft** |

### Reference

| # | Directory | Covers | Primary Personas | Status |
|---|-----------|--------|-----------------|--------|
| 25 | `existing-screens/` | Full inventory of all current QuantumPACS frontend screens with data contracts, API endpoints, and frontend expectations (583 lines). Reference for backend refactoring/API versioning. | All | **Draft** |

### Role-Based Requirements

Persona-based companions to the feature docs. Each role doc maps the role's workflows
(from `docs/requirements/<role>/` packages) to frontend data needs — what screens the
role uses, what data/actions they require, and the gaps that must be raised with backend.

| # | Directory | Role | Covers | Status |
|---|-----------|------|--------|--------|
| 26 | `role-super-admin/` | R01 Super Admin | Tenants, users, roles, routing, service keys, integrations, replicas, logs, metrics, DICOMweb/FHIR/HL7 admin, notifications | **Draft** |
| 27 | `role-tenant-admin/` | R02 Tenant Admin | Tenant-scoped subset of R01: users, roles, worklist, routing, keys, replicas, logs, metrics, integrations | **Draft** |
| 28 | `role-service-director/` | R03 Service Director | KPI dashboard, capacity heatmap, protocol compliance, SLA tracking, drill-through, report builder, exports, access audit | **Draft** |
| 29 | `role-service-coordinator/` | R04 Service Coordinator | Schedule board, exam assignment, STAT triage, utilization, staffing roster, conflicts, handoff report, calendar | **Draft** |
| 30 | `role-qa-team/` | R05 QI/QA Team | QA review queue + form, protocol registry, QA scores, corrective actions, incidents, peer review | **Draft** |
| 31 | `role-technologist/` | R06 Technologist | Modality worklist, patient verification, protocol, acquisition + QA, dose, safety checks, completion/handoff, incidents, override | **Draft** |
| 32 | `role-technician/` | R07 Technician | Same operator flow as R06 + fluoroscopy (live/spot/cine/DAP) and mammography (CC/MLO, compression, AGD) workflows | **Draft** |
| 33 | `role-staff-radiologist/` | R12 Staff Radiologist | Viewer, study browser, worklist, measurements, shares, audit, reporting (gap), resident review queue, peer review | **Draft** |
| 34 | `role-resident/` | R13 Resident | Supervised worklist, split-screen interpretation, draft reports, attending review, teaching files, exam log, feedback | **Draft** |
| 35 | `role-referring-clinician/` | R14 Referring Clinician | Read-only share-link viewer, report display via share, expiry handling, optional SSO | **Draft** |
| 36 | `role-teleradiologist/` | R18 Teleradiologist | Remote worklist, prelim→final reports, critical findings escalation, offline packages, multi-site, consultations | **Draft** |
| 37 | `role-front-desk/` | R08 Front Desk | Patient search + dedup, registration, order intake, scheduling, check-in, consent, insurance, queue board (all GATED) | **Draft** |
| 38 | `role-cashier/` | R09 Cashier | Invoices/payments, receipts, claims status, reconciliation, refunds, quotes, read-only clinical context (all GATED) | **Draft** |
| 39 | `role-biomedical-engineer/` | R10 Biomedical Engineer | Equipment registry, PM/QC, downtime, tickets, vendor contracts, alerts, uptime reporting (all GATED) | **Draft** |
| 40 | `role-nursing/` | R11 Nursing | Nursing worklist, prep checklist, vitals, contrast, allergy/safety, adverse reactions, sedation, MAR, handoff (all GATED) | **Draft** |
| 41 | `role-external-ris/` | R15 External RIS | HL7 ORM/ORU order exchange, DICOM MWL/MPPS, report delivery; partial — HL7/worklist/DICOMweb/FHIR scaffolding exists | **Draft** |
| 42 | `role-external-emr/` | R16 External EMR | HL7 ADT demographics, FHIR Patient/DiagnosticReport, results status; partial — ADT/FHIR/Webhooks exist | **Draft** |
| 43 | `role-external-pacs/` | R17 External PACS | DICOM C-STORE/C-FIND/C-MOVE, DICOMweb QIDO/WADO/STOW, routing/archive sync; partial — DICOMweb/upload/routing exist | **Draft** |
| 44 | `role-hospital-staff/` | R19 Hospital Staff | Scoped patient lookup, read-only study/report view, order awareness, results notification (portal GATED) | **Draft** |

> **Coverage note**: requirements packages exist for **all 19 roles** in
> `docs/requirements/` (every role has full 8-artifact packages: 01–08 +
> `README.md` + `CHANGELOG.md`). Role backend-requirements docs now exist for
> **all 19 roles** (rows 26–44): the 11 originally-packaged roles plus the 8
> newly-covered roles R08–R11 (front-desk, cashier, biomedical-engineer, nursing)
> and R15–R17, R19 (external RIS/EMR/PACS, hospital staff).
>
> **Codebase alignment (revised 2026-08-03)**: every package's artifact 04 now
> includes a **Role-Based Routing & Navigation (Presentation Layer)** section and
> every README a **Codebase Alignment** section. These are grounded in
> `role-presentation-layer.md` (verified against `frontend/src/` and
> `backend/api/routes.py`): they list the routes/sidebar items the role can actually
> reach today, the permission gates that control them, and mark aspirational v3.0
> features **GATED** (kept in the spec, flagged to backend).
>
> Doc status is independent of package status: packages may be approved/final
> (e.g., R01 approved, R03/R05/R14 final) while their role docs are new drafts.

### Reference

| # | Directory | Covers | Status |
|---|-----------|--------|--------|
| 45 | `role-presentation-layer.md` | Codebase ground truth for role-based UI routing, navigation gating (Sidebar.tsx permission map), frontend routes, backend API surface, and the 34-permission catalog — used to align all `docs/requirements/<role>/` packages with the actual codebase | **Verified 2026-08-03** |

## How to Use

1. **Find your feature**: Browse the table above or the directory listing in `.claude/docs/ai/`. Each directory is named by feature area.
2. **Read the doc**: Each document follows the same structure — Context → Screens/Components (each with Purpose, Data I need, Actions, States, Business rules) → Uncertainties → Questions for Backend → Discussion Log.
3. **Persona check**: The Persona→Feature mapping table shows which personas each feature serves. If you're changing shared behavior (e.g., search), check all linked docs.
4. **Status awareness**: Documents marked **Draft** are still evolving. **Planned** documents are outlines for future features. **Final** documents are considered stable.
5. **Cross-reference**: Some features are tightly coupled — e.g., `search/` + `study-list/` + `dicomweb/` (fallback). Check related directories for interface contracts.
6. **Role docs**: For persona-driven work, check `role-*/` docs (rows 26–44). They translate the `docs/requirements/<role>/` packages into frontend data needs and flag backend gaps (e.g., R12 reporting, R18 offline packages).
7. **Discuss uncertainties**: Each doc ends with a list of unresolved questions. When implementing, open a discussion with the frontend team to resolve these.

## Status Legend

| Status | Meaning |
|--------|---------|
| **Planned** | Feature not yet implemented; doc is a speculative requirements outline |
| **Draft** | Feature partially or fully implemented; doc captures current frontend expectations but may have gaps |
| **Review** | Doc has been reviewed by both frontend and backend teams; awaiting sign-off |
| **Final** | Doc is stable; implementation may continue but doc changes require formal update |
