# UI/UX Requirements — External PACS (R17)

## System Interface Surface (Presentation Layer)

The External PACS is a system-to-system integration: it has **no web UI**. Access is
API-driven via DICOMweb + DICOM C-STORE/C-FIND/C-MOVE. Verified against
`backend/api/routes.py`.

### Endpoints Exposed (codebase reality)

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /dicomweb/studies`, `GET /dicomweb/studies/{uid}/series`, `.../instances` | Query/retrieve (C-FIND/QIDO-RS) | API key |
| `GET /dicomweb/studies/{uid}` (+ series/instance) | WADO-RS (retrieve pixels) | API key |
| `GET /wado` | WADO-URI | API key |
| `POST /files/upload`, `GET /files/download.zip` | C-STORE-equivalent upload, bulk download | Auth + `FILE_WRITE` |
| `/files/{id}/data`, `/files/{id}/thumbnail` | Instance data + thumbnails | Auth |

### Interface Gating

- **Implemented**: DICOMweb QIDO-RS/WADO-RS study→series→instance drill-down,
  WADO-URI, file upload (C-STORE-equivalent), bulk download, routing rules to
  destinations (`/routing`).
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): C-MOVE
  retrieve workflow, archive synchronization UI, migration/backfill tooling.

## Screens & Navigation

The external PACS is a system actor with **no end-user UI**. Its surface is the
existing **DICOMweb admin + replicas** screens used by R01/R02:

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | DICOMweb Admin | Sidebar → DICOMweb | Station AE management, capabilities |
| 2 | Replicas | Sidebar → Replicas | Storage replica health, sync, failover |
| 3 | Routing Rules | Sidebar → Routing | Routing rule conditions + test + match counts |
| 4 | Metrics | Sidebar → Metrics | Store latency, Q/R timing, error rates, storage usage |

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| AETable | Nodes | Skeleton | "No AEs" | Retry | — | — |
| AEForm | Fields | — | — | Inline errors | Saved | During submit |
| ConnectivityBadge | Status | Spinner | — | Failed → retry | Up | — |
| ReplicaCard | Health | Spinner | — | Sync lag → alert | Synced | — |
| RoutingTable | Rules | Skeleton | "No rules" | Retry | — | — |

## Design System Conformance

- Tokens: `--color-success`, `--color-danger`, `--color-warning`, `--bg-surface`, mono font for AE/UID values.
- Components: reuse `Table`, `Form`, `Tag`, `Card`, `Progress`, `Popconfirm`; new `AEForm`, `ConnectivityBadge` specs.

## Accessibility Requirements

- WCAG 2.2 AA for the admin surface: keyboard-navigable tables, focus rings, contrast ≥ 4.5:1, non-color status indicators.

## Responsive Behavior

- Desktop-first admin surface; no mobile requirement (system integration).

## UX Principles Applied

- AE lifecycle visible with connectivity state; replica sync lag color + textual; routing rules testable one-click; status never color-only.
