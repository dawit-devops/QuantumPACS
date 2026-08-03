# R07 — Radiology Technician Requirements Package

| Field | Value |
|-------|-------|
| **Version** | 1.2.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Technicians access the study browser, viewer (image QC), the worklist
(`WORKLIST_READ`), and the shared exam console (`/exams` + `/exams/:id` — the same
lifecycle as R06; no separate technician UI).

**Backend** (`backend/api/exams.py`, routes in `backend/api/routes.py`): the shared
exam lifecycle is shipped — `/exams` (list/create), `/exams/{id}` (detail/update,
identity-confirm, protocol, acquisitions + accept/reject/retake decision, dose,
safety-checks, complete, incidents, overrides) and `/protocols`. Tables `exams`,
`acquisitions`, `safety_checks`, `incidents`, `protocol_overrides`, `protocols`
exist in `backend/db/exams.py`.

**Permissions** (`backend/api/permissions.py`): `EXAM_READ`/`EXAM_WRITE`/
`WORKLIST_READ`/`WORKLIST_WRITE`; the `technologist` built-in role grants these
(there is no dedicated `technician` role — technicians are covered by the same
grants).

**Implemented**: FR-R07-01..08 (shared exam lifecycle — see traceability for
endpoint mapping). **GATED** (kept as v3.0 spec): FR-R07-09 fluoroscopy-specific
workflow (live mode, spot/cine, DAP tracking — no `dap` field in `acquisitions`
schema, no `/fluoroscopy-*` endpoints) and FR-R07-10 mammography-specific workflow
(CC/MLO, compression monitoring, AGD — no `agd` field, no mammo-specific endpoints).
Also GATED (v3.1/v3.2): FR-R07-11 AI-assisted image QA, FR-R07-12 dose
optimization, FR-R07-13 RIS protocol selection.

---

## Role Profile

| Attribute | Detail |
|-----------|--------|
| **ID** | R07 |
| **Role** | Radiology Technician |
| **Persona** | Operator (per exam) — Operates DR, CR, Fluoroscopy, Mammography; positioning, acquisition, image QC, retakes, exam completion |
| **Access Tier** | Operator (per exam) |
| **Top Tasks (by frequency)** | 1. Exam preparation and patient positioning (per exam)<br>2. Image acquisition and QA (per exam)<br>3. Dose documentation (per exam)<br>4. Exam completion and handoff to radiologist (per exam)<br>5. Patient safety checks before contrast (fluoroscopy only)<br>6. Retake/incident logging (as needed) |
| **Pain Points** | • No real-time image QA — quality issues discovered after exam is complete<br>• Dose tracking is manual or not tracked per acquisition<br>• Patient safety checks are ad-hoc — no structured checklist in the system<br>• Exam completion handoff is manual — technician must notify radiologist separately<br>• Retake/incident logging is spreadsheet-based — no structured digital logging<br>• Protocol parameters are not displayed in the system — technician must reference paper protocols<br>• Fluoroscopy dose tracking (DAP) is not automated |
| **Devices** | Desktop workstation (primary), modality-specific console; dual-monitor standard for worklist + viewer |
| **Working Patterns** | Per-exam workflow; continuous acquisition; real-time QA; reactive (incident logging); handoff to radiologist |
| **PHI Exposure** | Patient initials and MRN last 4 digits shown on worklist; full PHI accessible via exam detail modal per HIPAA minimum necessary |

---

## Artifact Index

| # | File | Description | v3.0 Status |
|---|------|-------------|-------------|
| 01 | `01-user-requirements.md` | Functional (FR-R07-NN) & Non-Functional (NFR-R07-NN) requirements, MoSCoW prioritized | **Complete (v3.0 Must — 10 FRs)** |
| 02 | `02-workflow-maps.md` | 5 end-to-end workflow maps as Mermaid sequenceDiagrams with R04/R05/R12/R15/R16/R17 integration touchpoints | **Complete** |
| 03 | `03-user-stories.md` | User stories (US-R07-NN) with Given/When/Then ACs, WCAG 2.2 AA, performance targets | **Complete (10 v3.0 stories)** |
| 04 | `04-ui-ux-requirements.md` | Screen inventory (8 screens), component state matrix, design token references (existing + 8 proposed), a11y, responsive | **Complete** |
| 05 | `05-metrics-slas.md` | Quantified KPIs (M-R07-NN) with targets, measurement methods, frequency, owners; SLA tiers | **Complete (10 KPIs)** |
| 06 | `06-acceptance-criteria.md` | Validator-gated AC matrix mapped to FR/NFR IDs; verification methods; out-of-scope | **Complete (~40 v3.0 ACs)** |
| 07 | `07-traceability.md` | FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts | **Complete** |
| 08 | `08-implementation-roadmap.md` | Dependency-ordered implementation plan with status (done/partial/missing) per artifact | **Complete** |

---

## v3.0 vs v3.1 Scope Split

### v3.0 (Must Priority — This Package)
- FR-R07-01: Modality Worklist (auto-refresh, STAT highlighting)
- FR-R07-02: Patient Identity Verification (confirm patient before exam)
- FR-R07-03: Exam Protocol Selection (review parameters before acquisition)
- FR-R07-04: Image Acquisition and QA (real-time preview, reject/accept)
- FR-R07-05: Dose Documentation (auto-log, cumulative tracking, ACR benchmark)
- FR-R07-06: Patient Safety Checks (allergy, pregnancy, contrast for fluoroscopy)
- FR-R07-07: Exam Completion and Handoff (notify radiologist, push to PACS)
- FR-R07-08: Retake/Incident Logging (structured logging, notifications)
- FR-R07-09: Fluoroscopy-Specific Workflow (live mode, spot/cine, DAP tracking)
- FR-R07-10: Mammography-Specific Workflow (CC/MLO, compression monitoring, AGD)

### v3.1 (Should/Could — Deferred)
- FR-R07-09: Fluoroscopy workflow enhancements (preset fluoroscopy protocols)
- FR-R07-10: Mammography workflow enhancements (tomosynthesis support)
- FR-R07-11: AI-assisted image QA (auto-detect artifacts, positioning errors)
- FR-R07-12: Automated dose optimization suggestions
- FR-R07-13: Integration with RIS for automated protocol selection

---

## Cross-Role Dependencies

| Dependency | Source Role | Integration | Field Mapping / API Contract |
|------------|-------------|-------------|------------------------------|
| **Exam Assignment** | R04 Coordinator → R07 | WebSocket (LISTEN/NOTIFY) | R04 assigns exam → R07 worklist updates in ≤5s |
| **Exam Completion Push** | R07 → R12 Radiologist | WebSocket (LISTEN/NOTIFY) | R07 completes exam → R12 worklist updates in ≤5s |
| **Incident/Retake Data** | R07 → R05 QA Team | `incidents` table | R07 logs incidents → R05 QA review queue |
| **Patient Demographics** | R16 EMR → R07 | HL7 ADT | R16 sends patient demographics → R07 shows on exam detail |
| **Allergy/Pregnancy Data** | R16 EMR → R07 | HL7 ADT | R16 sends allergy/pregnancy flags → R07 safety check panel |
| **Image Archive Push** | R07 → R17 PACS | DICOM C-STORE | R07 triggers PACS push on exam completion |
| **Scheduled Exam Feed** | R15 RIS → R07 | HL7 ORM | R15 sends scheduled orders → R07 worklist auto-populates |

---

## New API Endpoints Required (v3.0)

> **Status 2026-08-03**: FR-R07-01..08 endpoints are **shipped** in
> `backend/api/routes.py` (v2 prefix; see Codebase Alignment) via the shared exam
> lifecycle. Patient confirmation is `/api/v2/exams/{id}/identity-confirm`,
> acquisition decision is `/api/v2/exams/{id}/acquisitions/{acquisition_id}/{decision}`,
> and the technician worklist is the shared `/api/v2/worklist` (modality filter) —
> no dedicated `/worklists/technician`. FR-R07-09 fluoroscopy endpoints
> (`/fluoroscopy-start`, `/spot-capture`, `/cine-start`, `/cine-stop`) are **NOT
> shipped** — no fluoroscopy-specific endpoints exist.

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|------------|
| `/api/v2/worklists/technician` | GET | Fetch technician worklist — shipped as `/api/v2/worklist` (modality filter) | `WORKLIST_READ` |
| `/api/v2/exams/{id}` | GET | Fetch exam detail with patient + protocol | `EXAM_READ` |
| `/api/v2/exams/{id}/confirm-patient` | POST | Confirm patient identity — shipped as `/api/v2/exams/{id}/identity-confirm` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/protocol` | GET | Fetch protocol parameters | `EXAM_READ` |
| `/api/v2/exams/{id}/start-acquisition` | POST | Start image acquisition — shipped as `/api/v2/exams/{id}/acquisitions` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/acquire` | POST | Record image acquisition with dose — shipped as `/api/v2/exams/{id}/acquisitions/{acquisition_id}/{decision}` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/reject` | POST | Flag image as rejected — same acquisition-decision endpoint | `EXAM_WRITE` |
| `/api/v2/exams/{id}/dose-baseline` | GET | Fetch cumulative dose + ACR benchmark — shipped as `/api/v2/exams/{id}/dose` | `EXAM_READ` |
| `/api/v2/exams/{id}/dose-log` | POST | Log dose parameters — shipped as `/api/v2/exams/{id}/dose` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/safety-check` | POST | Record safety check confirmation — shipped as `/api/v2/exams/{id}/safety-checks` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/complete` | POST | Mark exam complete, push to PACS, notify radiologist | `EXAM_WRITE` |
| `/api/v2/exams/{id}/incident` | POST | Log incident with severity — shipped as `/api/v2/exams/{id}/incidents` | `EXAM_WRITE` |
| `/api/v2/exams/{id}/fluoroscopy-start` | POST | Start fluoroscopy live mode — **NOT SHIPPED** (FR-R07-09 GATED) | `EXAM_WRITE` |
| `/api/v2/exams/{id}/spot-capture` | POST | Capture spot image — **NOT SHIPPED** (FR-R07-09 GATED) | `EXAM_WRITE` |
| `/api/v2/exams/{id}/cine-start` | POST | Start cine recording — **NOT SHIPPED** (FR-R07-09 GATED) | `EXAM_WRITE` |
| `/api/v2/exams/{id}/cine-stop` | POST | Stop cine recording — **NOT SHIPPED** (FR-R07-09 GATED) | `EXAM_WRITE` |

---

## New Permission Slugs Required

> **Status 2026-08-03**: shipped in `backend/api/permissions.py` — `WORKLIST_READ`,
> `WORKLIST_WRITE`, `EXAM_READ`, `EXAM_WRITE` (there is no dedicated `technician`
> built-in role; the `technologist` role carries these grants):

```python
# backend/api/permissions.py
WORKLIST_READ = 'WORKLIST_READ'
EXAM_READ = 'EXAM_READ'
EXAM_WRITE = 'EXAM_WRITE'

# Built-in role (technician is covered by this role's grants)
BUILT_IN_ROLES['technologist'] = [
    Permission.FILE_READ.value, Permission.FILE_WRITE.value, Permission.FILE_DELETE.value,
    Permission.PATIENT_READ.value, Permission.PATIENT_WRITE.value,
    Permission.STUDY_READ.value, Permission.STUDY_WRITE.value,
    Permission.WORKLIST_READ.value, Permission.WORKLIST_WRITE.value,
    Permission.EXAM_READ.value, Permission.EXAM_WRITE.value,
    Permission.DICOMWEB_READ.value,
]
```

---

## Database Schema Extensions (1 New Table)

### New for R07

> **Status 2026-08-03**: shipped in `backend/db/exams.py` — the table is named
> `acquisitions` (not `image_acquisitions`). The spec's `dap` (fluoroscopy) and
> `agd` (mammography) columns are **NOT in the schema** — this is the blocking
> dependency for FR-R07-09/10:

```sql
CREATE TABLE acquisitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id         UUID REFERENCES exams(id) NOT NULL,
    study_uid       VARCHAR(100) NOT NULL,
    series_uid      VARCHAR(100) NOT NULL,
    instance_number INTEGER NOT NULL,
    modality        VARCHAR(20) NOT NULL,
    kvp             NUMERIC,
    mas             NUMERIC,
    exposure_time   NUMERIC,
    dlp             NUMERIC,
    -- dap             NUMERIC,      -- NOT SHIPPED — GATED (FR-R07-09)
    -- agd             NUMERIC,      -- NOT SHIPPED — GATED (FR-R07-10)
    ctdiovol        NUMERIC,
    slice_thickness NUMERIC,
    status          VARCHAR(20) DEFAULT 'acquired', -- 'acquired', 'accepted', 'rejected'
    reject_reason   VARCHAR(50),
    reject_description TEXT,
    reject_count    INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_acquisitions_exam ON acquisitions(exam_id);
CREATE INDEX idx_acquisitions_status ON acquisitions(status);
CREATE INDEX idx_acquisitions_study ON acquisitions(study_uid);
```

---

## Design System Extensions (8 New Semantic Tokens)

| Semantic Token | Primitive Ref / Value | Description |
|----------------|----------------------|-------------|
| `acquisition-stat-bg` | `rgba(239, 68, 68, 0.1)` | Background for STAT exam blocks on worklist |
| `acquisition-reject-bg` | `#FEE2E2` | Background for rejected image indicators |
| `acquisition-accept-bg` | `#D1FAE5` | Background for accepted image indicators |
| `dose-warning-bg` | `#FEF3C7` | Background for dose warning banner |
| `dose-danger-bg` | `#FEE2E2` | Background for dose limit exceeded banner |
| `safety-alert-bg` | `#FEF2F2` | Background for safety warning banners |
| `fluoro-live-bg` | `rgba(239, 68, 68, 0.05)` | Background for live fluoroscopy mode indicator |
| `mammo-compression-bg` | `#FEF3C7` | Background for compression pressure warning |

---

## New Component Specs (Add to `component-specs.md`)

| Component | States | Key Tokens | Behavior |
|-----------|--------|-----------|----------|
| **TechnicianWorklist** | loading, empty, populated, error | `--bg-surface`, `--color-danger`, `--color-warning` | Extends existing worklist with DR/CR/Fluoroscopy/Mammography filtering, auto-refresh (30s), STAT highlighting, keyboard navigation |
| **ExamDetailPanel** | idle, loading, confirmed, error | `--bg-surface`, `--color-primary` | Slide-out panel with patient demographics, protocol info, confirm button; transitions to acquisition view on confirm |
| **ProtocolPanel** | idle, loading, error, started | `--bg-surface`, `--color-danger` | Displays protocol parameters (views, kVp, mAs, SID, grid); safety conflict warnings; start button |
| **AcquisitionView** | idle, acquiring, paused, complete | `--color-danger`, `--color-warning` | Cornerstone3D viewer with QA overlay; accept/reject buttons; dose panel sidebar; keyboard shortcuts |
| **QAOverlay** | idle, accept, reject, warning | `--color-success`, `--color-danger` | Real-time image quality indicators (exposure, positioning, artifact flags); overlay on Cornerstone3D viewer |
| **DosePanel** | idle, loading, warning, danger | `--color-warning`, `--color-danger` | Live dose tracking with cumulative total and ACR benchmark comparison; color-coded warnings |
| **SafetyCheckModal** | idle, loading, error, confirmed | `--color-danger`, `--color-warning` | Modal for allergy/pregnancy safety checks before contrast; confirmation checkbox required |
| **IncidentLogModal** | idle, loading, error, submitted | `--bg-surface`, `--color-danger` | Modal for logging incidents with type, severity, description; notifications to R05/R12 |
| **FluoroscopyWorkflow** | idle, live, spot, cine, complete | `fluoro-live-bg`, `--color-danger` | Live fluoroscopy + spot capture + cine recording + DAP tracker; keyboard shortcuts |
| **MammographyWorkflow** | idle, cc, mlo, complete | `mammo-compression-bg`, `--color-primary` | CC/MLO view selection + compression monitoring + AGD tracker |

---

## Quality Gate Checklist

- [x] All 8 files exist with correct ID prefixes (FR-R07, NFR-R07, US-R07, AC-R07, M-R07)
- [x] Every FR has ≥1 AC; every AC links to FR/NFR
- [x] All 4 states (loading/empty/error/success) specified per component
- [x] Performance targets quantified (LCP ≤2s, preview ≤500ms, handoff ≤5s)
- [x] 16 API endpoints flagged with request/response shapes
- [x] WCAG 2.2 AA ACs concrete (keyboard, focus, contrast, ARIA, inline validation)
- [x] 5 Mermaid workflow diagrams (W1-W5, including incident logging)
- [x] R04/R05/R12/R15/R16/R17 integration stubs documented (API contracts)
- [x] Design tokens: 8 proposed semantic tokens + existing references
- [x] Validator gate: every AC observable/measurable; reverse validation noted
- [x] Cross-role deps matrix (R04, R05, R12, R15, R16, R17)
- [x] Out-of-scope explicitly listed

---

## Out of Scope (Explicit)

- MRI/PET/CT/Ultrasound acquisition (R06) — technician operates DR/CR/Fluoroscopy/Mammography only
- Patient registration (R08) — technician does not register patients
- Scheduling (R04) — coordinator schedules; technician executes
- QA protocol management (R05) — separate role with its own requirements package
- DICOM image viewing/measurement tools for diagnostic interpretation (R12/R18) — technician uses viewer for QA, not for diagnostic interpretation
- PACS archive management (R01/R02) — backend handles PACS push; technician triggers it
- AI/CAD integration (v3.2+ roadmap) — not in v3.0 scope
- Mobile native app — PWA only; mobile view is responsive adaptation
- Radiologist diagnostic interpretation (R12/R18) — technician acquires images, radiologist interprets
- Contrast administration — technician triggers, nurse (R11) administers
- Patient consent — handled by registration (R08) and nursing (R11)
- Critical findings escalation (R12/R18) — technician logs incidents; radiologist manages escalation
- Billing (R09) — outside technician scope
- Shift handoff report (R04) — coordinator generates; technician contributes data
- Utilization dashboard (R04) — coordinator views; technician data feeds it
- Staffing roster (R04) — coordinator manages; technician is assigned
- Audit log retention policy (R01) — system manages retention; technician generates entries

---

*Generated by pacs-requirements-architect skill pipeline. See `CLAUDE.md` Section 8 for methodology.*