# Traceability Matrix — Qa Team (R05)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R05-01 | Yes | AC-R05-01, AC-R05-02, AC-R05-03, AC-R05-04, AC-R05-05, AC-R05-06, AC-R05-07, AC-R05-08, AC-R05-09, AC-R05-10 | Covered |
| FR-R05-02 | Yes | AC-R05-11, AC-R05-12, AC-R05-13, AC-R05-14, AC-R05-15, AC-R05-16, AC-R05-17, AC-R05-18, AC-R05-19, AC-R05-20 | Covered |
| FR-R05-03 | Yes | AC-R05-21, AC-R05-22, AC-R05-23, AC-R05-24, AC-R05-25, AC-R05-26, AC-R05-27, AC-R05-28, AC-R05-29, AC-R05-30, AC-R05-31, AC-R05-32, AC-R05-33 | Covered |
| FR-R05-04 | Yes | AC-R05-34, AC-R05-35, AC-R05-36, AC-R05-37, AC-R05-38, AC-R05-39, AC-R05-40, AC-R05-41, AC-R05-42, AC-R05-43 | Covered |
| FR-R05-05 | Yes | AC-R05-44, AC-R05-45, AC-R05-46, AC-R05-47, AC-R05-48, AC-R05-49, AC-R05-50, AC-R05-51, AC-R05-52, AC-R05-53, AC-R05-54 | Covered |
| FR-R05-06 | Yes | AC-R05-55, AC-R05-56, AC-R05-57, AC-R05-58, AC-R05-59, AC-R05-60, AC-R05-61, AC-R05-62, AC-R05-63, AC-R05-64 | Covered |
| FR-R05-07 | Yes | AC-R05-65, AC-R05-66, AC-R05-67, AC-R05-68, AC-R05-69, AC-R05-70, AC-R05-71 | Covered |
| FR-R05-08 | Yes | AC-R05-72, AC-R05-73, AC-R05-74, AC-R05-75, AC-R05-76, AC-R05-77, AC-R05-78, AC-R05-79 | Covered |
| FR-R05-09 | Yes | AC-R05-80, AC-R05-81, AC-R05-82, AC-R05-83, AC-R05-84, AC-R05-85, AC-R05-86, AC-R05-87 | Covered |
| FR-R05-10 | Yes | AC-R05-153 | Covered — implemented |
| FR-R05-11 | Yes | AC-R05-151 | Covered (GATED — v3.1) |
| FR-R05-12 | Yes | AC-R05-152 | Covered (GATED — v3.1) |
| FR-R05-13 | No | — | Gap — no AC yet (GATED — v3.2) |
| NFR-R05-01 | Yes | AC-R05-88..93 | Covered |
| NFR-R05-02 | Yes | AC-R05-94..97 | Covered |
| NFR-R05-03 | Yes | AC-R05-98..103 | Covered |
| NFR-R05-04 | Yes | AC-R05-104..108 | Covered |
| NFR-R05-05 | Yes | AC-R05-109..119 | Covered |
| NFR-R05-06 | Yes | AC-R05-120..124 | Covered |
| NFR-R05-07 | Yes | AC-R05-125..130 | Covered |
| NFR-R05-08 | Yes | AC-R05-131..136 | Covered |
| NFR-R05-09 | Yes | AC-R05-137..140 | Covered |
| NFR-R05-10 | Yes | AC-R05-141..150 | Covered |

## Implementation Status (codebase reality, verified 2026-08-03)

The QA module is implemented end-to-end (backend `api/qa.py`, routes in
`routes.py`; frontend `frontend/src/qa/`). FR-R05-01..07 and FR-R05-10 map to
shipped endpoints; FR-R05-08/09/11/12/13 remain GATED (v3.1/v3.2 scope):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R05-01 (QA review queue) | Covered — implemented | `GET /qa/queue` (`QAQueue.tsx`, `/qa/queue`) |
| FR-R05-02 (QA review workflow) | Covered — implemented | `GET/PUT /qa/reviews/{exam_id}`, `POST /qa/reviews` (`QAReviewForm.tsx`) |
| FR-R05-03 (protocol registry CRUD) | Covered — implemented | `GET/POST /qa/protocols`, `GET/PUT/DELETE /qa/protocols/{id}` (`ProtocolRegistry.tsx`); also `/protocols` for exam console |
| FR-R05-04 (QA score persistence) | Covered — implemented | `qa_scores` write via review submit (`/qa/reviews` PUT/POST) |
| FR-R05-05 (corrective action inbox) | Covered — implemented | `GET/POST /qa/corrective-actions`, `POST /qa/corrective-actions/{id}/resolve` (`CorrectiveActions.tsx`) |
| FR-R05-06 (incident/retake logging) | Covered — implemented | `GET/POST /qa/incidents`, `POST /qa/incidents/{id}/resolve` (`Incidents.tsx`) |
| FR-R05-07 (RBAC QA role) | Covered — implemented | `qa_team` built-in role in `permissions.py` (`QA_READ`/`QA_WRITE`/`PROTOCOL_MANAGE`/`PEER_REVIEW_*`/`DICOMWEB_READ`/`METRICS_READ`) |
| FR-R05-08 (automated dose validation) | GATED | No rules engine or dose-baseline job (v3.1) |
| FR-R05-09 (DICOM tag validation rules) | GATED | No DICOM tag parser/rules engine (v3.1) |
| FR-R05-10 (peer review workflow) | Covered — implemented | `GET /qa/reviewers`, `POST /peer-reviews`, `POST /peer-reviews/{id}/submit`; R12 PeerReviewInbox |
| FR-R05-11 (ACR phantom QA) | GATED | No phantom scheduling/analysis (v3.1) |
| FR-R05-12 (regulatory reporting) | GATED | No reporting engine (v3.1) |
| FR-R05-13 (AI-assisted QA) | GATED | No AI inference integration (v3.2) |
| NFR-R05-* tied to implemented FRs | Covered | FR-R05-01..07, 10 above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | Each US maps to ≥1 FR |
| 01 User Requirements | 06 Acceptance Criteria | Each FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | Each workflow step with user decision → US |
| 03 User Stories | 04 UI/UX Requirements | Each US component → state spec |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |
| 05 Metrics & SLAs | 06 Acceptance Criteria | Each metric target → measurable AC |
| 07 Traceability Matrix | 08 Implementation Roadmap | Roadmap derived from traceability gaps |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R05 QI/QA Team | Consumes exam completion | R06 Technologist | Exam completion trigger → QA queue entry |
| R05 QI/QA Team | Provides compliance data | R03 Service Director | QA scores → protocol compliance dashboard |
| R05 QI/QA Team | Assigns peer review | R12 Staff Radiologist | Peer review task → radiologist inbox |
| R05 QI/QA Team | Receives corrective actions | R03 Service Director | Gap analysis → corrective-action assignment |
| R05 QI/QA Team | Uses audit/incident data | R01 Super Admin | Audit log + incidents read access |
