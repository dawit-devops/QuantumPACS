# Backend Requirements: R05 Radiology QI/QA Team

## Context

The QI/QA Team audits exam quality, tracks protocol compliance, logs and
investigates incidents, manages the protocol registry, tracks corrective actions,
and coordinates peer reviews. Queue-driven workflow with forms-heavy data entry;
QA scores written here feed the R03 Service Director's compliance dashboard.
Exam completion by technologists (R06) should auto-populate the QA queue.

**Screens (new)**: QA Review Queue, QA Review Form, Protocol Registry CRUD,
Corrective Action Inbox, Incident/Retake Logging, Peer Review Workflow.

**Personas**: P4 (QA). **Access tier**: read + QA tools
(`QA_READ`, `QA_WRITE`, `PROTOCOL_MANAGE`).

## Screens/Components

### QA Review Queue

**Purpose**: Filterable, paginated queue of studies awaiting QA review.

**Data I need to display**: per row — study reference, protocol, priority
(STAT/escalated/routine), status (pending/in_review/completed/skipped), assigned
reviewer, timestamps.

**Actions**: filter by status/priority/assigned, open a study for review, skip.

**States to handle**: empty queue, loading, error; a study the reviewer has no
access to (must still render but not open).

**Business rules affecting UI**:
- Exam completion from R06 must create queue entries automatically (WebSocket
  push or poll — needs a contract).
- Priority affects badge color and ordering.

### QA Review Form

**Purpose**: Record pass/fail verdict, dose values, and sequence compliance.

**Data I need to display**: study metadata (patient/study/protocol), protocol
required-sequences checklist, dose fields (DLP, CTDIvol, kVp, mAs) with units,
ACR benchmark reference values for comparison.

**Actions**: mark pass/fail, enter dose values, complete sequence checklist,
add comments (≤500 chars), submit.

**States to handle**: loading review data, validating, submitting, error,
unsaved-changes warning.

**Business rules affecting UI**: pass/fail is required; dose fields numeric with
unit suffixes; submission persists to QA scores and updates the queue status.

### Protocol Registry CRUD

**Purpose**: Maintain protocols with required sequences and ACR benchmarks.

**Data I need**: protocol code, name, modality, body part, required sequences
(add/remove rows), ACR benchmark key-value entries.

**Actions**: create/edit/delete protocol, search/filter the registry.

**States to handle**: empty registry, invalid benchmark input, delete of a
protocol referenced by QA scores (backend's call).

### Incident/Retake Logging

**Purpose**: Log retakes and incidents linked to studies.

**Data I need**: original study UID, repeat study UID (optional), incident type
(positioning/artifact/protocol deviation/motion/equipment/contrast), description,
reported-by, resolution state.

**Actions**: create incident, mark resolved, view history.

**Business rules affecting UI**: incident creation should notify the responsible
technologist (R06) via in-app notification.

### Corrective Action Inbox

**Purpose**: Receive, track, and close corrective actions.

**Data I need**: action source (R03/R05/R06), linked protocol + study UIDs, issue
description, assignee, status (open/in_progress/resolved), findings/actions
fields.

**Actions**: open/expand, record findings and actions taken, mark resolved.

### Peer Review Workflow

**Purpose**: Assign studies for second-opinion reads and compare findings.

**Data I need**: peer review records — study, original report reference, assigned
radiologist (R12), assigner, findings, discrepancy level (none/minor/major/
critical), escalation flag, status.

**Actions**: assign a peer review to a radiologist, view submitted findings
side-by-side with the original report, flag discrepancy, escalate.

**Business rules affecting UI**: major/critical discrepancies must be visible and
escalatable; the side-by-side comparison needs both the original report and the
peer findings.

## Uncertainties
- [ ] Queue auto-population on exam completion — is it a push (WebSocket) or does
  the UI poll?
- [ ] Are the ACR benchmark values stored per-protocol (backend) or supplied by
  the frontend for display?
- [ ] Peer review lifecycle: can a review be reassigned, and who can edit a
  submitted review?
- [ ] Incident → technologist notification wiring: does an incident create a
  notification event, or is that manual?
- [ ] RBAC slugs `QA_READ`/`QA_WRITE`/`PROTOCOL_MANAGE` are proposed but need
  confirmation.

## Questions for Backend
- What event contract drives QA queue creation on exam completion?
- Should protocol registry be shared across tenants or per-tenant?
- For corrective actions created from R03 gap analysis — do they arrive via API
  or notification, and what shape?

## Discussion Log

_(pending backend review)_
