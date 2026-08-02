# User Requirements — Radiology & Imaging Service QI/QA Team (R05)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Functional Requirements (v3.0 Must Priority)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R05-01 | **QA Review Queue**: Display filterable, paginated queue of exams awaiting QA review. Columns: Accession, Patient (initials only), Modality, Protocol, Scheduled Date, Priority (routine/STAT/escalated), Status (pending/in_review/completed/skipped). Filters: modality, status, date range, priority. Pagination: 50 exams/page with virtualization. Auto-refresh ≤1min. | Must | New `QAQueueTable` component; extends `Table` with status badges |
| FR-R05-02 | **QA Review Workflow**: Exam detail page with "Open in Viewer" link (opens `/files/{study_uid}` in new tab) + QA form (right side): Pass/Fail radio group (large touch targets 44×44px), Dose fields (DLP mGy·cm, CTDIvol mGy, kVp, mAs) with inline validation, Sequence checklist (dynamic based on protocol.required_sequences JSONB), Comments textarea (max 500 chars), Submit (primary) / Cancel (secondary) buttons. On submit → `qa_scores` INSERT → queue status='completed'. | Must | New `QAReviewForm` component; form-heavy |
| FR-R05-03 | **Protocol Registry CRUD**: Manage protocols with CRUD table + "Add Protocol" button → modal form. Fields: Protocol Code (unique, alphanumeric), Name, Modality (dropdown: CT/MR/US/DX/MG/FL/PET), Body Part, Required Sequences (dynamic list: add/remove rows with sequence name, phase, contrast boolean), ACR Benchmark (key-value pairs editor: max_dlp_mgycm, max_ctdivol_mgy, min_snr). Validation: code unique, ≥1 sequence required, ACR benchmarks numeric. | Must | New `ProtocolCRUDModal` component; complex form with dynamic lists |
| FR-R05-04 | **QA Score Persistence**: On QA form submit, write to `qa_scores` table with: protocol_id, study_uid, sequence_compliance (JSONB map: sequence→boolean), dose_dlp, dose_ctdivol, dose_kvp, dose_mas, pass_fail, comments, reviewed_by (user ID), reviewed_at (timestamp). Trigger R03 dashboard refresh (protocol compliance scorecard reads from `qa_scores`). | Must | Feeds R03 FR-R03-03; database write transaction |
| FR-R05-05 | **Corrective Action Inbox**: Receive corrective actions assigned by R03 Service Director (via `POST /api/v2/qa/corrective-actions`). Display as notification-style card list: Source (R03/R05_self/R06), Issue Description, Study UIDs (expandable list), Assigned Date, Status (open/in_progress/resolved), Actions: Review (expand card), Close (modal: findings textarea + actions taken textarea → UPDATE status='resolved', resolved_at). In-app notification badge on sidebar when new action assigned. | Must | New `CorrectiveActionCard` component; expandable cards |
| FR-R05-06 | **Incident/Retake Logging**: Log incidents with form: Study UID (search/autocomplete), Repeat Study UID (optional, search/autocomplete), Incident Type (dropdown: positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), Description (textarea, max 500 chars), Submit → `incidents` INSERT. Notify R06 technologist (in-app notification) if incident requires retraining. Display incident list table (filterable by type, date range, resolved status). | Must | New incident log form; links two studies; notification to R06 |
| FR-R05-07 | **RBAC QA Role**: New built-in role `qa_team` with permissions: `FILE_READ` (view studies), `STUDY_READ` (view metadata), `QA_READ`, `QA_WRITE`, `PROTOCOL_MANAGE`. Sidebar shows: Study List, QA Queue, Protocols, Incidents, Corrective Actions, Peer Review, Dashboard (personal), Account. No access to Users, Tenants, Roles, Logs, Replicas (admin-only). Tenant-scoped. | Must | Add to `backend/api/permissions.py` BUILT_IN_ROLES |
| FR-R05-10 | **Peer Review Workflow**: QA lead assigns peer review to second radiologist (R12): Assignment form (study search, radiologist picker dropdown filtered by role=R12, reason dropdown: critical_finding/trainee_read/random_audit/complaint) → `POST /api/v2/qa/peer-review` → R12 receives in-app notification. Peer review list table: Study, Original Reader, Peer Reviewer, Status (assigned/in_progress/completed), Discrepancy Badge (none/minor/major/critical), Actions: View Comparison (modal: side-by-side original report + peer review findings), Escalate (if major/critical, modal to notify R03). R12 submits findings via `PUT /api/v2/qa/peer-review/{id}` (cross-role endpoint). | Must | New `PeerReviewAssignmentForm`, `PeerReviewComparisonModal`; cross-role R05↔R12 |

---

## Functional Requirements (v3.1 Deferred — Should/Could)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R05-08 | **Automated Dose Validation**: On exam ingestion (C-STORE), auto-check dose (DLP, CTDIvol) against protocol.acr_benchmark. If exceeds DRL, flag in queue with warning badge, auto-create corrective action assigned to QA lead for review. Requires rules engine. | Should | Requires background job + rules engine; v3.1 |
| FR-R05-09 | **DICOM Tag Validation Rules**: On exam ingestion, validate required sequences present in DICOM tags (SeriesDescription, ProtocolName) against protocol.required_sequences. Flag missing sequences in queue. Requires DICOM tag parser + rules engine. | Should | Requires DICOM tag introspection; v3.1 |
| FR-R05-11 | **ACR Phantom QA**: Schedule phantom scans (weekly/monthly per modality), auto-analyze phantom images (CNR, SNR, uniformity) against ACR thresholds, flag failures, track phantom QA compliance rate. | Should | Requires phantom image analysis library; v3.1 |
| FR-R05-12 | **Regulatory Reporting**: Export compliance reports for MQSA (mammography), ACR, state-specific requirements. Templates: dose summary, protocol compliance, incident log, peer review discrepancies. Formats: CSV, PDF, ACR XML. | Could | Regulatory templates vary by jurisdiction; v3.1+ |
| FR-R05-13 | **AI-assisted QA**: Integrate AI models to auto-detect artifacts (motion, noise, positioning errors) and flag in queue. Optional: suggest retake before radiologist read. | Could | Requires AI inference integration; v3.2+ |

---

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R05-01 | QA queue load (LCP) | ≤ 2s | Lighthouse CI, RUM |
| NFR-R05-02 | QA form submission latency (API) | ≤ 500ms | Backend timing |
| NFR-R05-03 | Queue refresh staleness (new exams appear) | ≤ 1min | Synthetic probe (Grafana) |
| NFR-R05-04 | Protocol CRUD save latency (API) | ≤ 300ms | Backend timing |
| NFR-R05-05 | Incident log save latency (API) | ≤ 500ms | Backend timing |
| NFR-R05-06 | WCAG 2.2 AA compliance | 100% (forms keyboard-intensive) | axe-core CI + manual |
| NFR-R05-07 | Form field validation | Real-time inline errors (≤200ms) | Frontend timing |
| NFR-R05-08 | Concurrent QA reviewers | ≥ 10 | k6 WebSocket scenario |
| NFR-R05-09 | Queue pagination (virtualization) | 50 exams/page, smooth scroll (60fps) | react-window performance |
| NFR-R05-10 | Token compliance | 100% (no one-off colors) | Stylelint custom rule + manual |

---

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Full study access for QA review (HIPAA minimum necessary); aggregated metrics (no PHI); incident reports (patient identifiers for investigation only) | FR-R05-01, FR-R05-06, NFR-R05-06 |
| A2 | 9 new API endpoints required (flagged for `frontend-to-backend-requirements`) | All FRs |
| A3 | R06 exam completion trigger: When R06 marks exam complete, `POST /api/v2/qa/queue` with `{study_uid, protocol_id, priority}` — **R05 documents API contract; R06 must implement the call** | FR-R05-01, cross-role R06→R05 |
| A4 | R12 peer review: R05 assigns (`POST /api/v2/qa/peer-review`), R12 submits (`PUT /api/v2/qa/peer-review/{id}`) — **R05 documents API; R12 must implement peer review inbox + form** | FR-R05-10, cross-role R05↔R12 |
| A5 | 5 new database tables (protocols, qa_scores, qa_queue, incidents, corrective_actions, peer_reviews) — Alembic migration required | FR-R05-03, FR-R05-04, FR-R05-01, FR-R05-06, FR-R05-05, FR-R05-10 |
| A6 | Protocol.required_sequences is JSONB array: `[{"sequence": "Venous", "phase": "contrast", "contrast": true}]` — Dynamic form must handle add/remove | FR-R05-03 |
| A7 | ACR benchmarks are JSONB key-value: `{"max_dlp_mgycm": 500, "max_ctdivol_mgy": 25, "min_snr": 10}` — Flexible for CT/MR/MG | FR-R05-03 |
| A8 | Viewer integration: Link to `/files/{study_uid}` (opens in new tab), not embedded Cornerstone3D — Simpler, consistent with R03 drill-through | FR-R05-02 |
| A9 | Design system: 4 new semantic tokens (`qa-pass-bg`, `qa-fail-bg`, `incident-warning-bg`, `corrective-action-bg`) + existing tokens | All UI requirements |
| A10 | Tenant isolation: All QA data scoped to tenant via `X-Tenant-ID` / JWT tenant claim | All FRs |

---

## API Gap Summary (for Backend Team)

| Endpoint | Method | Description | Request/Response Shape |
|----------|--------|-------------|------------------------|
| `/api/v2/qa/queue` | GET | QA review queue | Query: `?modality=CT&status=pending&page=1&limit=50`<br>Response: `{items: [{id, study_uid, accession, patient_initials, modality, protocol, priority, status, created_at}], total, page}` |
| `/api/v2/qa/queue` | POST | Create queue entry (from R06) | Body: `{study_uid, protocol_id, priority}`<br>Response: `201 + {id}` |
| `/api/v2/qa/review/{study_uid}` | GET | Get QA review detail | Response: `{study: {uid, accession, patient_initials, modality, scheduled_date}, protocol: {id, code, name, required_sequences}, existing_score?: {pass_fail, dose_dlp, ...}}` |
| `/api/v2/qa/review/{study_uid}` | POST | Submit QA score | Body: `{protocol_id, pass_fail, dose_dlp, dose_ctdivol, dose_kvp, dose_mas, sequence_compliance: {Venous: true, ...}, comments}`<br>Response: `201 + {qa_score_id}` |
| `/api/v2/qa/protocols` | GET | List protocols | Query: `?modality=CT`<br>Response: `{protocols: [{id, code, name, modality, body_part, required_sequences, acr_benchmark}]}` |
| `/api/v2/qa/protocols` | POST | Create protocol | Body: `{code, name, modality, body_part, required_sequences, acr_benchmark}`<br>Response: `201 + {id}` |
| `/api/v2/qa/protocols/{id}` | GET/PUT/DELETE | Single protocol CRUD | PUT Body: same as POST<br>Response: `200/204` |
| `/api/v2/qa/incidents` | GET/POST | Incident/retake logging | POST Body: `{study_uid, repeat_study_uid?, incident_type, description}`<br>Response: `201 + {incident_id}` |
| `/api/v2/qa/corrective-actions` | GET/POST/PUT | Corrective action inbox | POST Body: `{source, protocol_id?, study_uids, issue_description, assigned_to}`<br>PUT Body: `{id, status, findings, actions_taken, resolved_at?}`<br>Response: `200/201` |
| `/api/v2/qa/peer-review` | POST | Assign peer review | Body: `{study_uid, assigned_to, reason}`<br>Response: `201 + {peer_review_id}` |
| `/api/v2/qa/peer-review/{id}` | PUT | Submit peer review findings (from R12) | Body: `{peer_review_findings, discrepancy_level, discrepancy_description}`<br>Response: `200` |

---

## Permission Additions (backend/api/permissions.py)

```python
# New permission slugs
QA_READ = 'QA_READ'
QA_WRITE = 'QA_WRITE'
PROTOCOL_MANAGE = 'PROTOCOL_MANAGE'

# Add to PERMISSION_GROUPS
PERMISSION_GROUPS['QA'] = [
    'QA_READ', 'QA_WRITE', 'PROTOCOL_MANAGE'
]

# New built-in role
BUILT_IN_ROLES['qa_team'] = [
    Permission.FILE_READ.value,      # View studies in Files
    Permission.STUDY_READ.value,     # View study metadata
    'QA_READ',
    'QA_WRITE',
    'PROTOCOL_MANAGE',
]
```

---

## Database Migration DDL (5 New Tables)

**Alembic migration**: `backend/migrations/versions/XXX_qa_schema.py`

```sql
-- From R03 (already specified, created with this migration)
CREATE TABLE protocols (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_code   VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    modality        VARCHAR(20) NOT NULL,
    body_part       VARCHAR(50),
    required_sequences JSONB NOT NULL,
    acr_benchmark   JSONB,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

COMMENT ON COLUMN protocols.required_sequences IS 'Array of objects: [{"sequence": "Venous", "phase": "contrast", "contrast": true}]';
COMMENT ON COLUMN protocols.acr_benchmark IS 'Key-value pairs: {"max_dlp_mgycm": 500, "max_ctdivol_mgy": 25, "min_snr": 10}';

CREATE TABLE qa_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id         UUID REFERENCES protocols(id),
    study_uid           VARCHAR(100) NOT NULL,
    sequence_compliance JSONB,
    dose_dlp            NUMERIC,
    dose_ctdivol        NUMERIC,
    dose_kvp            NUMERIC,
    dose_mas            NUMERIC,
    pass_fail           BOOLEAN NOT NULL,
    comments            TEXT,
    reviewed_by         UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_qa_scores_protocol ON qa_scores(protocol_id);
CREATE INDEX idx_qa_scores_study ON qa_scores(study_uid);

-- New for R05
CREATE TABLE qa_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_uid       VARCHAR(100) REFERENCES studies(study_instance_uid) ON DELETE CASCADE,
    protocol_id     UUID REFERENCES protocols(id),
    assigned_to     UUID REFERENCES users(id),
    priority        VARCHAR(20) DEFAULT 'routine',
    status          VARCHAR(20) DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_qa_queue_status ON qa_queue(status) WHERE status IN ('pending', 'in_review');
CREATE INDEX idx_qa_queue_assigned ON qa_queue(assigned_to, status);

CREATE TABLE incidents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_uid           VARCHAR(100) NOT NULL,
    repeat_study_uid    VARCHAR(100),
    incident_type       VARCHAR(50) NOT NULL,
    reported_by         UUID REFERENCES users(id),
    description         TEXT,
    resolved            BOOLEAN DEFAULT false,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_incidents_type ON incidents(incident_type, resolved);

CREATE TABLE corrective_actions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source              VARCHAR(50) NOT NULL,
    protocol_id         UUID REFERENCES protocols(id),
    study_uids          JSONB,
    issue_description   TEXT NOT NULL,
    assigned_to         UUID REFERENCES users(id),
    assigned_by         UUID REFERENCES users(id),
    status              VARCHAR(20) DEFAULT 'open',
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
    original_report_id          UUID,
    assigned_to                 UUID REFERENCES users(id),
    assigned_by                 UUID REFERENCES users(id),
    peer_review_findings        TEXT,
    discrepancy_level           VARCHAR(20),
    discrepancy_description     TEXT,
    escalated                   BOOLEAN DEFAULT false,
    status                      VARCHAR(20) DEFAULT 'assigned',
    assigned_at                 TIMESTAMPTZ DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_peer_reviews_assigned ON peer_reviews(assigned_to, status);
CREATE INDEX idx_peer_reviews_discrepancy ON peer_reviews(discrepancy_level) WHERE discrepancy_level IN ('major', 'critical');
```

---

## Integration Contract for R06 Technologist (To Be Implemented in R06 Package)

**Contract**: When R06 marks exam complete, call `POST /api/v2/qa/queue`.

**Trigger**: Exam completion event (e.g., all images received, technologist marks "Complete" in worklist, or auto-trigger on last C-STORE instance for study).

**Request**:
```json
POST /api/v2/qa/queue
Content-Type: application/json
X-Auth-Pacs: <jwt>

{
  "study_uid": "1.2.840.113619.2.55.3...",
  "protocol_id": "uuid-of-protocol-from-protocols-table",
  "priority": "routine"  // or "stat" for urgent exams
}
```

**Response**:
```json
201 Created
{
  "id": "uuid-of-queue-entry",
  "study_uid": "1.2.840.113619.2.55.3...",
  "status": "pending",
  "created_at": "2026-08-02T17:30:00Z"
}
```

**Error Handling**:
- 400 if `study_uid` not found in studies table
- 404 if `protocol_id` not found in protocols table
- 409 if queue entry already exists for this study_uid (duplicate)

**R06 Responsibility**: Implement this API call in technologist workflow; handle errors gracefully (retry on 500, log on 400/404).

---

## Integration Contract for R12 Staff Radiologist (To Be Implemented in R12 Package)

### Contract 1: Peer Review Assignment (R05 → R12)

**Flow**: R05 assigns peer review → R12 receives in-app notification → R12 inbox shows pending peer review.

**API**: `POST /api/v2/qa/peer-review` (called by R05, creates `peer_reviews` entry).

**R12 Requirement**: R12 must have **Peer Review Inbox** UI showing assigned peer reviews with link to study viewer.

### Contract 2: Peer Review Submission (R12 → R05)

**Flow**: R12 performs QA read → submits findings via form → R05 receives for comparison.

**API**: `PUT /api/v2/qa/peer-review/{id}`

**Request**:
```json
PUT /api/v2/qa/peer-review/{id}
Content-Type: application/json
X-Auth-Pacs: <jwt>

{
  "peer_review_findings": "Second opinion narrative text...",
  "discrepancy_level": "minor",  // 'none', 'minor', 'major', 'critical'
  "discrepancy_description": "Discrepancy notes if level != none"
}
```

**Response**: `200 OK`

**R12 Responsibility**: Implement peer review submission form; handle errors gracefully.