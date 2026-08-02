# Backend Requirements: R18 Teleradiologist

## Context

The Teleradiologist reads remotely for off-hours coverage, preliminary/STAT
reads, second opinions, and consultations — across multiple hospital sites and
time zones. High-acuity, time-sensitive (STAT reads ≤30 min, critical findings
communicated within 15 min). Shares the core viewer/reporting toolset with R12
but needs: a **remote worklist** (site + priority filtering), **preliminary vs
final report states**, **critical-findings escalation**, **offline study
packages**, **multi-site access/tenant switching**, and **consultation
workflow**. Full PHI access; everything must be audited (access, views, exports
with IP).

**Screens (new/planned on top of the R12 viewer)**: Remote Worklist, Report
Editor (prelim→final), Critical Findings escalation, Offline Package download,
Site selector, Consultation workflow.

**Personas**: P1 (remote radiologist). **Access tier**: full clinical read,
multi-site.

## Screens/Components

### Remote Worklist

**Purpose**: Prioritized reading list across covered sites.

**Data I need to display**: studies assigned to the teleradiologist with site
tag, priority (STAT urgent), modality, status (including preliminary vs final
for reports), assignment time; real-time updates as exams complete (R06/R07).

**Actions**: filter by site/priority/status, open study, sort.

**States to handle**: loading, empty, error, low-bandwidth warning, offline
indicator.

**Business rules affecting UI**: worklist must clearly distinguish preliminary
reports needing finalization from new reads.

### Viewer + Report Editor (shared with R12)

**Purpose**: Read and report remotely.

**Data I need**: full viewer (hierarchy, WADO-RS, thumbnails, annotations), plus
the reporting state machine (draft → preliminary → final). Preliminary reports
must be visually marked.

**Actions**: create preliminary report, finalize (transition state), review
priors, request consultation.

**States to handle**: preliminary vs final badges; finalize validation; report
version history.

### Critical Findings Escalation

**Purpose**: Guarantee critical findings reach the on-call clinician fast.

**Data I need**: critical-finding record (study, finding, target clinician,
status, timestamps).

**Actions**: trigger escalation → out-of-band notification (email/SMS/pager)
with acknowledgement tracking.

**States to handle**: sent, acknowledged, escalated-if-unacknowledged.

**Business rules affecting UI**: ACR guideline — critical findings communicated
within 15 min; escalation latency is measured and reported to R03/R05.

### Offline Study Package

**Purpose**: Download studies for connectivity-lost scenarios.

**Data I need**: a downloadable package (format TBD — DICOMDIR vs encrypted ZIP
vs PWA cache) with integrity metadata.

**Actions**: request package, download, resume.

**States to handle**: packaging in progress, ready, failed, expired.

### Multi-site Access / Consultation

**Purpose**: Switch sites and request second opinions.

**Data I need**: list of sites/tenants the user can access, active site state,
consultation requests/responses.

**Actions**: switch site, open consultation, respond.

## Uncertainties
- [ ] Offline package format is an open question (DICOMDIR? encrypted ZIP? PWA
  cache?) — blocks the download UX design.
- [ ] Multi-site credentials: single SSO across tenants, or per-tenant
  credentials?
- [ ] Mobile viewer scope: full diagnostic reading or consultative review only?
- [ ] Preliminary report finalization: auto-assignment to on-site R12, or manual?
- [ ] Critical-findings escalation channel and acknowledgement semantics need a
  contract.
- [ ] Bandwidth: minimum WAN speed for diagnostic reading and a fallback for
  low-bandwidth scenarios are unspecified.
- [ ] Do preliminary → final state transitions get logged for liability
  (malpractice defense)?

## Questions for Backend
- Is the remote worklist a distinct endpoint with site/priority filtering, or a
  parameterized view of the R12 worklist?
- For offline packages, does the backend generate them on request (async job) or
  on ingest?
- What is the report state machine contract shared between R12, R13, and R18?

## Discussion Log

_(pending backend review)_
