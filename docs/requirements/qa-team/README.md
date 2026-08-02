# R05 — Radiology & Imaging Service QI/QA Team Requirements Package

| Field | Value |
|-------|-------|
| **Version** | 1.2.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

---

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". **None of the QA-specific screens exist** in the codebase — no `/qa/*`
routes, no `qa_*` tables, no `qa_team` built-in role, no `QA_*` permission slugs.
QA reviewers today can only view studies in the Files browser + viewer (read-only).

**Implemented**: shared Files/viewer (study browsing for QA review). **GATED**
(kept as v3.0 spec): FR-R05-01..08, FR-R05-10..13 — all QA queue/review/protocol/
incident/corrective-action/peer-review features; requires backend QA module
(endpoints + 5 tables) and `QA_READ`/`QA_WRITE`/`PROTOCOL_MANAGE` permissions.

---

## Role Profile

| Attribute | Detail |
|-----------|--------|
| **ID** | R05 |
| **Role** | Radiology & Imaging Service QI/QA Team |
| **Persona** | Quality assurance specialists responsible for exam quality audits, protocol compliance tracking, incident investigation, and regulatory compliance. Work in QA office; review exams daily; manage protocol registry; track corrective actions; coordinate peer reviews. |
| **Access Tier** | Read + QA tools (write QA scores, manage protocols, log incidents, assign peer reviews) |
| **Top Tasks (by frequency)** | 1. Daily QA exam review (mark pass/fail, enter dose, check sequences) — continuous<br>2. Incident/retake logging and investigation (daily)<br>3. Protocol registry management (weekly)<br>4. Corrective action tracking and resolution (daily)<br>5. Peer review assignment and discrepancy analysis (weekly) |
| **Pain Points** | • No structured QA workflow — spreadsheet-based tracking<br>• Protocol compliance data scattered across PACS/modality consoles/paper logs<br>• No dose validation against ACR benchmarks<br>• Incident tracking manual (email/paper forms)<br>• Peer review assignment ad-hoc, no systematic tracking<br>• No real-time QA queue visibility |
| **Devices** | Desktop workstation (primary), tablet for rounding; dual-monitor standard for exam review + viewer side-by-side |
| **Working Patterns** | Queue-driven workflow; exam-by-exam review; forms-heavy data entry; weekly protocol governance; regulatory reporting (monthly/quarterly) |
| **PHI Exposure** | Full study access for QA review (HIPAA minimum necessary); aggregated compliance metrics (no PHI); incident reports (patient identifiers required for investigation + corrective action) |

---

## Artifact Index

| # | File | Description | v3.0 Status |
|---|------|-------------|-------------|
| 01 | `01-user-requirements.md` | Functional (FR-R05-NN) & Non-Functional (NFR-R05-NN) requirements, MoSCoW prioritized | **Complete (v3.0 Must — 8 FRs)** |
| 02 | `02-workflow-maps.md` | 5 end-to-end workflow maps as Mermaid sequenceDiagrams with R03/R06/R12 integration touchpoints | **Complete** |
| 03 | `03-user-stories.md` | User stories (US-R05-NN) with Given/When/Then AC, WCAG 2.2 AA, performance targets | **Complete (13 v3.0 stories)** |
| 04 | `04-ui-ux-requirements.md` | Screen inventory (6 screens), component state matrix, design token references (existing + 4 proposed), A11y, responsive | **Complete** |
| 05 | `05-metrics-slas.md` | Quantified KPIs (M-R05-NN) with targets, measurement methods, frequency, owners; SLA tiers | **Complete (14 KPIs)** |
| 06 | `06-acceptance-criteria.md` | Validator-gated AC matrix mapped to FR/NFR IDs; verification methods; out-of-scope | **Complete (~95 v3.0 ACs)** |
| 07 | `07-traceability.md` | FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts | **Complete** |
| 08 | `08-implementation-roadmap.md` | Dependency-ordered implementation plan with status (done/partial/missing) per artifact | **Complete** |

---

## v3.0 vs v3.1 Scope Split

### v3.0 (Must Priority — This Package)
- FR-R05-01: QA Review Queue (filterable, paginated, status-driven)
- FR-R05-02: QA Review Workflow (pass/fail, dose entry, sequence checklist)
- FR-R05-03: Protocol Registry CRUD (manage protocols with required sequences, ACR benchmarks)
- FR-R05-04: QA Score Persistence (`qa_scores` table write → feeds R03 compliance dashboard)
- FR-R05-05: Corrective Action Inbox (receive from R03, track resolution, close with findings)
- FR-R05-06: Incident/Retake Logging (log retakes with reason, link original + repeat study UIDs)
- FR-R05-07: RBAC QA Role (permissions: `QA_READ`, `QA_WRITE`, `PROTOCOL_MANAGE`)
- FR-R05-10: Peer Review Workflow (assign to R12, compare findings, flag discrepancies)

### v3.1 (Should/Could — Deferred)
- FR-R05-08: Automated Dose Validation (flag studies exceeding DRL, requires rules engine)
- FR-R05-09: DICOM Tag Validation Rules (auto-check required sequences per protocol)
- FR-R05-11: ACR Phantom QA (scheduled phantom scans, auto-analysis)
- FR-R05-12: Regulatory Reporting (MQSA, ACR, state-specific exports)
- FR-R05-13: AI-assisted QA (auto-detect artifacts, positioning issues)

---

## Cross-Role Dependencies

| Dependency | Source Role | Integration | Field Mapping / API Contract |
|------------|-------------|-------------|------------------------------|
| **Protocol Compliance Data** | R05 → R03 Service Director | `qa_scores` table (read) | R05 writes QA scores → R03 reads for protocol compliance dashboard (FR-R03-03) |
| **Corrective Action Assignment** | R03 → R05 | `POST /api/v2/qa/corrective-actions` | R03 gap analysis assigns action → R05 inbox receives notification |
| **Exam Completion Trigger** | R06 Technologist → R05 | `POST /api/v2/qa/queue` | R06 marks exam complete → R05 queue entry auto-created with `{study_uid, protocol_id, priority}` |
| **Incident Feedback** | R05 → R06 | `incidents` table + notification | R05 logs incident → R06 notified for retraining (in-app notification) |
| **Peer Review Assignment** | R05 → R12 Staff Radiologist | `POST /api/v2/qa/peer-review` | R05 assigns peer review → R12 receives assignment in peer review inbox |
| **Peer Review Submission** | R12 → R05 | `PUT /api/v2/qa/peer-review/{id}` | R12 performs QA read → submits findings → R05 receives for comparison |

---

## New API Endpoints Required (v3.0)

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|------------|
| `/api/v2/qa/queue` | GET | QA review queue (filtered, paginated) | `QA_READ` |
| `/api/v2/qa/queue` | POST | Create queue entry (from R06 on exam complete) | `QA_WRITE` |
| `/api/v2/qa/review/{study_uid}` | GET | Get QA review detail + form data | `QA_READ` |
| `/api/v2/qa/review/{study_uid}` | POST | Submit QA score (pass/fail + dose) | `QA_WRITE` |
| `/api/v2/qa/protocols` | GET/POST | Protocol registry CRUD list/create | `PROTOCOL_MANAGE` |
| `/api/v2/qa/protocols/{id}` | GET/PUT/DELETE | Single protocol CRUD | `PROTOCOL_MANAGE` |
| `/api/v2/qa/incidents` | GET/POST | Incident/retake logging | `QA_WRITE` |
| `/api/v2/qa/corrective-actions` | GET/POST/PUT | Corrective action inbox CRUD | `QA_READ` / `QA_WRITE` |
| `/api/v2/qa/peer-review` | POST | Assign peer review to radiologist | `QA_WRITE` |
| `/api/v2/qa/peer-review/{id}` | PUT | Submit peer review findings (from R12) | R12 permission |

---

## New Permission Slugs Required

```python
# In backend/api/permissions.py
QA_READ = 'QA_READ'
QA_WRITE = 'QA_WRITE'
PROTOCOL_MANAGE = 'PROTOCOL_MANAGE'

# Add to PERMISSION_GROUPS
PERMISSION_GROUPS['QA'] = [
    'QA_READ', 'QA_WRITE', 'PROTOCOL_MANAGE'
]

# New built-in role
BUILT_IN_ROLES['qa_team'] = [
    Permission.FILE_READ.value,      # View studies
    Permission.STUDY_READ.value,     # View study metadata
    'QA_READ',
    'QA_WRITE',
    'PROTOCOL_MANAGE',
]
```

---

## Database Schema Extensions (5 New Tables)

### From R03 (Already Specified, Created with R05 Migration)

```sql
CREATE TABLE protocols (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_code   VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    modality        VARCHAR(20) NOT NULL,
    body_part       VARCHAR(50),
    required_sequences JSONB NOT NULL, -- [{"sequence": "Venous", "phase": "contrast", "contrast": true}]
    acr_benchmark   JSONB,            -- {"max_dlp_mgycm": 500, "max_ctdivol_mgy": 25, "min_snr": 10}
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE qa_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id         UUID REFERENCES protocols(id),
    study_uid           VARCHAR(100) NOT NULL,
    sequence_compliance JSONB,        -- {"Venous": true, "Arterial": false}
    dose_dlp            NUMERIC,      -- Dose Length Product (mGy·cm)
    dose_ctdivol        NUMERIC,      -- CTDIvol (mGy)
    dose_kvp            NUMERIC,      -- kVp
    dose_mas            NUMERIC,      -- mAs
    pass_fail           BOOLEAN NOT NULL,
    comments            TEXT,
    reviewed_by         UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

### New for R05

```sql
CREATE TABLE qa_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_uid       VARCHAR(100) REFERENCES studies(study_instance_uid) ON DELETE CASCADE,
    protocol_id     UUID REFERENCES protocols(id),
    assigned_to     UUID REFERENCES users(id),
    priority        VARCHAR(20) DEFAULT 'routine', -- 'routine', 'stat', 'escalated'
    status          VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_review', 'completed', 'skipped'
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_qa_queue_status ON qa_queue(status) WHERE status IN ('pending', 'in_review');
CREATE INDEX idx_qa_queue_assigned ON qa_queue(assigned_to, status);

CREATE TABLE incidents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_uid           VARCHAR(100) NOT NULL,
    repeat_study_uid    VARCHAR(100),
    incident_type       VARCHAR(50) NOT NULL, -- 'positioning', 'artifact', 'protocol_deviation', 'patient_motion', 'equipment_malfunction', 'contrast_extravasation'
    reported_by         UUID REFERENCES users(id),
    description         TEXT,
    resolved            BOOLEAN DEFAULT false,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE corrective_actions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source              VARCHAR(50) NOT NULL, -- 'R03_director', 'R05_self', 'R06_tech'
    protocol_id         UUID REFERENCES protocols(id),
    study_uids          JSONB,        -- ["1.2.3...", "1.2.4..."]
    issue_description   TEXT NOT NULL,
    assigned_to         UUID REFERENCES users(id),
    assigned_by         UUID REFERENCES users(id),
    status              VARCHAR(20) DEFAULT 'open', -- 'open', 'in_progress', 'resolved'
    findings            TEXT,
    actions_taken       TEXT,
    assigned_at         TIMESTAMPTZ DEFAULT now(),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_corrective_actions_assigned ON corrective_actions(assigned_to, status);

CREATE TABLE peer_reviews (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_uid                   VARCHAR(100) NOT NULL,
    original_report_id          UUID, -- References reports table (R12 scope)
    assigned_to                 UUID REFERENCES users(id), -- Second radiologist (R12)
    assigned_by                 UUID REFERENCES users(id), -- QA user (R05)
    peer_review_findings        TEXT,
    discrepancy_level           VARCHAR(20), -- 'none', 'minor', 'major', 'critical'
    discrepancy_description     TEXT,
    escalated                   BOOLEAN DEFAULT false,
    status                      VARCHAR(20) DEFAULT 'assigned', -- 'assigned', 'in_progress', 'completed'
    assigned_at                 TIMESTAMPTZ DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_peer_reviews_assigned ON peer_reviews(assigned_to, status);
CREATE INDEX idx_peer_reviews_discrepancy ON peer_reviews(discrepancy_level) WHERE discrepancy_level IN ('major', 'critical');
```

---

## Design System Extensions (4 New Semantic Tokens)

| Semantic Token | Primitive Ref / Value | Description |
|----------------|----------------------|-------------|
| `qa-pass-bg` | `#D1FAE5` | Light green background for pass badge/card |
| `qa-fail-bg` | `#FEE2E2` | Light red background for fail badge/card |
| `incident-warning-bg` | `#FEF3C7` | Amber background for incident cards |
| `corrective-action-bg` | `#DBEAFE` | Blue background for corrective action cards |

---

## New Component Specs (Add to `component-specs.md`)

| Component | States | Key Tokens | Behavior |
|-----------|--------|-----------|----------|
| **QAQueueTable** | loading, empty, populated, filtered | `--bg-surface`, `--table-radius`, status badges (gray/blue/green) | Extends Table with filterable columns, status badges, priority badges (STAT=red), "Review" action button per row |
| **QAReviewForm** | idle, validating, submitting, error | `--bg-surface`, `--color-primary`, `qa-pass-bg`, `qa-fail-bg` | Pass/Fail radio (large touch targets), dose fields (numeric + unit suffix), sequence checklist (dynamic), comments textarea (500 char max), Submit (primary) / Cancel (secondary) |
| **ProtocolCRUDModal** | idle, submitting, error | `--bg-surface`, `--color-primary` | Form modal: code, name, modality dropdown, body part, dynamic sequence list (add/remove rows), ACR benchmark key-value editor |
| **CorrectiveActionCard** | collapsed, expanded | `--bg-surface`, `corrective-action-bg`, status badges | Expandable card: header (source + issue + date + status badge), body (study UID list + findings textarea + actions textarea + Resolve button) |
| **PeerReviewComparisonModal** | loading, loaded | `--bg-surface`, `--text-primary` | Side-by-side view: original report (left) + peer review findings (right) + discrepancy radio (none/minor/major/critical) + Escalate button (if major/critical) |

---

## Quality Gate Checklist

- [x] All 8 files exist with correct ID prefixes (FR-R05, NFR-R05, US-R05, AC-R05, M-R05)
- [x] Every FR has ≥1 AC; every AC links to FR/NFR
- [x] All 4 states (loading/empty/error/success) specified per form/table
- [x] Performance targets quantified (LCP ≤2s, submit ≤500ms, queue ≤1min)
- [x] 9 API endpoints flagged with request/response shapes
- [x] WCAG 2.2 AA ACs concrete (keyboard, focus, contrast, ARIA, inline validation)
- [x] 5 Mermaid workflow diagrams (W1-W5, including peer review)
- [x] R03/R06/R12 integration stubs documented (API contracts)
- [x] Design tokens: 4 proposed semantic tokens + existing references
- [x] Validator gate: every AC observable/measurable; reverse validation noted
- [x] Cross-role deps matrix (R03, R06, R12)
- [x] Out-of-scope explicitly listed

---

## Out of Scope (Explicit)

- Radiologist reading workflow (R12) — peer review is R05 orchestration, but R12 performs the read
- Technologist acquisition workflow (R06/R07) — exam completion trigger is R06 responsibility
- Service Director analytics dashboards (R03) — R05 provides data, R03 consumes
- Patient registration (R08)
- Billing/cashier (R09)
- DICOM image viewing/measurement tools (Epic E3) — R05 links to Files viewer, no embedded Cornerstone3D
- Multi-site federation UI (v3.x per ADR)
- AI/CAD integration (v3.2 per PRD)
- Automated QA (dose validation, DICOM tag rules) — v3.1
- ACR phantom QA — v3.1
- Regulatory reporting (MQSA, ACR exports) — v3.1+

---

*Generated by pacs-requirements-architect skill pipeline. See `CLAUDE.md` Section 8 for methodology.*