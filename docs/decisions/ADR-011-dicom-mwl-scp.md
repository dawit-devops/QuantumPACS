# ADR-011: DICOM Modality Worklist (MWL) SCP

## Status
Accepted

## Date
2026-07-23

## Context
Modalities (CT, MR, XA, etc.) currently push studies to QuantumPACS via DICOM C-STORE with no ability to query for scheduled procedures. Technologists must manually enter patient demographics at the modality console for each exam, leading to data entry errors, exam delays, and duplicate patient records. The system needs a DICOM Modality Worklist service that allows modalities to pull scheduled procedure information via C-FIND MWL (SOP Class UID 1.2.840.10008.5.1.4.31).

Key requirements:
- Modalities query scheduled procedures by date, modality, patient ID, or accession number
- Admin/technologist web UI for managing worklist entries
- Automatic status tracking (scheduled → in_progress → performed)
- Matching of received studies to worklist entries
- Audit logging of all MWL queries

## Decision
Implement a DICOM MWL SCP using pynetdicom's C-FIND SCP support.

Key design choices:

1. **Worklist storage in PostgreSQL**: A new `worklist_entries` table stores all scheduled procedure data (patient demographics, procedure details, scheduling info, status, matched study reference). A `mwl_query_log` table captures all modality C-FIND requests for audit.

2. **MWL SCP server**: A dedicated pynetdicom AE instance running alongside the existing C-STORE SCP, listening on a configurable port (default 11113). Responds to C-FIND MWL requests by querying the `worklist_entries` table filtered by the modality's query parameters.

3. **Auto-matching at C-STORE time**: When a study arrives via C-STORE, the system checks if its accession number matches an active worklist entry. If matched, the entry transitions to `performed` and links to the study.

4. **Status model**: Entries start as `scheduled`, transition to `in_progress` automatically on first C-FIND query from a modality, and to `performed` when matched images arrive. Admins can manually set `cancelled`.

5. **Web UI**: CRUD interface for worklist entries (admin), read-only list with status filters (technologist), modality connection status dashboard (admin).

6. **Modality AET tracking**: Known modality AETs derived from query logs and C-STORE association history, stored in a `known_aets` table.

## Alternatives Considered

### External MWL proxy appliance
- Pros: No development effort, dedicated product
- Cons: Additional network hop, licensing cost, vendor lock-in, separate management UI
- Rejected: In-house implementation integrates with existing patient/study DB and UI

### RIS integration for worklist
- Pros: Single source of truth for orders
- Cons: Requires RIS vendor cooperation; most deployments don't have a live RIS feed; adds external dependency
- Rejected: QuantumPACS must be self-sufficient; RIS integration can be added later via HL7 ORM

### Manual procedure codes only (no modality query)
- Pros: No additional development
- Cons: Current broken workflow preserved; data entry errors continue; no exam efficiency gain
- Rejected: MWL is a core PACS feature

## Consequences
- Adds pynetdicom C-FIND SCP support alongside existing C-STORE SCP
- New `worklist_entries`, `mwl_query_log`, and `known_aets` database tables
- New Alembic migration(s) for schema changes
- New admin UI pages for worklist management and modality status
- Worklist entries auto-match to incoming studies by accession number
- Modality configuration requires pointing to the MWL SCP port
- Audit trail of all MWL queries for compliance
