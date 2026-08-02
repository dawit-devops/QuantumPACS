# Backend Requirements: R17 External PACS

## Context

The External PACS is a **system-to-system** integration (no web UI): it exchanges
images via DICOM C-STORE/C-FIND/C-MOVE and DICOMweb QIDO-RS/WADO-RS/STOW-RS. The
operational surface in QuantumPACS is the DICOMweb admin + replicas + routing
screens (used by R01/R02), but the PACS consumes the API directly. Failure
semantics: C-FIND timeout 30s, C-MOVE retrieve retry 2x, C-STORE ack ≤10s.

**Screens (existing)**: DICOMweb QIDO-RS/WADO-RS study→series→instance drill-down
(`/dicomweb/studies*`), WADO-URI (`/wado`), file upload (C-STORE-equivalent),
bulk download, routing rules (`/routing`) — see `dicomweb/`, `dicom-mwl-scp/`,
`routing-rules/`, `replicas/`.

**Personas**: P5 (Modalities/PACS). **Access tier**: API only (DICOM + DICOMweb).

## Interfaces

### Store / Query / Retrieve (C-STORE, C-FIND, C-MOVE)

**Purpose**: Accept, query, and retrieve studies.

**Data I need**: C-STORE associations (persist instances, return per-instance
status), C-FIND keysets (study/series/instance), C-MOVE retrieve requests.

**Actions**: store instances, serve queries, transfer instances to requesting AE.

**States to handle**: association accepted/rejected; transfer success/failure;
query timeout.

**Business rules affecting UI**: C-MOVE retrieve workflow is **GATED** — the
backend DICOM store exists but the full C-MOVE transfer flow is not wired.

### DICOMweb (QIDO-RS / WADO-RS / STOW-RS)

**Purpose**: Web-native query/retrieve/store.

**Data I need**: QIDO-RS search, WADO-RS pixels/metadata (frames, bulk data,
thumbnail), STOW-RS stores.

**Actions**: search studies, retrieve pixels (viewer), accept STOW-RS stores.

**Business rules affecting UI**: WADO-RS drives the viewer
(`frontend/src/dicomweb/`); progressive/lossy WADO-RS support is an open question
(see `viewer/`).

### Routing / Archive Sync / AE Management

**Purpose**: Route instances and manage endpoints.

**Data I need**: routing rules (all-matching-rules-applied semantics) with
delivery logs, storage replicas (local/S3/B2) for archive sync, AE nodes
(local + remote titles, addresses, ports, transfer syntaxes).

**Actions**: configure routing, trigger replica/archive sync, test AE
connectivity.

**Business rules affecting UI**: archive synchronization UI and migration/
backfill tooling are **GATED** (replica management exists; sync orchestration
does not).

## Uncertainties

- [ ] C-MOVE retrieve workflow, archive sync UI, and migration/backfill tooling
  are GATED — raise with backend.
- [ ] STOW-RS: is it exposed as a first-class endpoint or only the upload path?
- [ ] Archive sync integration with replicas (local/S3/B2) — is there a sync
  orchestration design?
- [ ] Progressive WADO-RS (low-res first) for the viewer — planned?

## Questions for Backend

- What is the roadmap for C-MOVE retrieve and archive-sync orchestration?
- Is the routing delivery log queryable for reconciliation, or config-only?
- How are AE nodes surfaced for connectivity testing today?

## Discussion Log

_(pending backend review)_
